# Target path: backend/app/risk/model.py
"""
ML / anomaly-scoring component: Isolation Forest over the behavioural feature
vector your brief specified. Kept separate from rules.py on purpose -- rules
are deterministic and individually explainable; this is a population-level
"how unusual is this account compared to everyone else in this batch" signal.

WHY ISOLATION FOREST (not a deeper model):
- Unsupervised -- there is no labeled fraud data for a hackathon dataset, and
  assuming there is would be dishonest.
- Handles multi-dimensional outliers directly, gives a continuous score.
- Fast enough at 100k-250k transaction scale.
- Matches the brief's own instruction: "practical and explainable... rather
  than an unnecessarily complex deep-learning model."

TWO-MODE DESIGN -- READ BEFORE WIRING THIS INTO THE API:
Isolation Forest needs a population to compare an account against. There is
no single "score this one account" call that makes sense in isolation.

  1. fit_anomaly_model(all_features) -- run ONCE per batch/dataset (e.g. when
     a dataset is uploaded), across every account you have features for.
     Returns an AnomalyModel that holds the fitted forest + scaler + the
     training population's raw scores (needed for percentile normalization).
  2. score_anomaly(model, one_account_features) -- fast, uses the already-fit
     model. This is what a live "/risk-score/{account_id}" endpoint calls,
     as long as it has the AnomalyModel object from step 1 (load it from
     wherever you persist it -- this module doesn't handle persistence).

Calling fit_anomaly_model with only one account's features will not raise an
error, but the result is meaningless -- there's nothing to be an outlier
relative to. See MIN_POPULATION_SIZE below.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from .schemas import RiskFeatures

# Isolation Forest needs enough accounts to have a meaningful notion of
# "unusual". Below this, fit_anomaly_model still runs (sklearn doesn't
# enforce a minimum) but score_anomaly refuses to report a score, because a
# percentile rank against fewer than ~20 points isn't a real signal.
MIN_POPULATION_SIZE = 20

# The exact feature vector from the brief. Order matters -- it must match
# between fit and score. network_degree falls back to unique_counterparties
# when the graph module hasn't supplied graph.graph_degree (documented in
# features_to_vector below).
FEATURE_NAMES: List[str] = [
    "transaction_count",
    "average_transaction_amount",
    "max_amount_deviation_ratio",
    "burst_velocity_score",
    "unique_receivers",
    "unique_senders",
    "distinct_device_count",
    "distinct_ip_count",
    "network_degree",
]


def features_to_vector(features: RiskFeatures) -> List[float]:
    network_degree = (
        features.graph.graph_degree
        if features.graph and features.graph.graph_degree is not None
        else features.unique_counterparties  # fallback proxy, documented above
    )
    return [
        float(features.transaction_count),
        float(features.average_transaction_amount),
        float(features.max_amount_deviation_ratio),
        float(features.burst_velocity_score),
        float(features.unique_receivers),
        float(features.unique_senders),
        float(features.distinct_device_count),
        float(features.distinct_ip_count),
        float(network_degree),
    ]


@dataclass
class AnomalyModel:
    forest: IsolationForest
    scaler: StandardScaler
    training_raw_scores: np.ndarray  # decision_function output for the training population
    training_mean: np.ndarray  # per-feature mean, for explaining WHY an account is anomalous
    training_std: np.ndarray   # per-feature std, same purpose
    population_size: int


def fit_anomaly_model(
    features_list: List[RiskFeatures],
    contamination: float = 0.1,
    random_state: int = 42,
) -> AnomalyModel:
    """
    Fits on the given population. `contamination` is Isolation Forest's own
    prior on what fraction of the population is expected to be anomalous --
    0.1 is sklearn's default and a reasonable starting point for a hackathon
    demo, NOT a claim that 10% of real accounts are laundering money. Tune it
    against your actual dataset's known injected-suspicious-account rate if
    you're using the synthetic generator (Step 8).
    """
    vectors = np.array([features_to_vector(f) for f in features_list])

    scaler = StandardScaler()
    scaled = scaler.fit_transform(vectors)

    forest = IsolationForest(contamination=contamination, random_state=random_state)
    forest.fit(scaled)

    raw_scores = forest.decision_function(scaled)  # higher = more normal, lower = more anomalous

    return AnomalyModel(
        forest=forest,
        scaler=scaler,
        training_raw_scores=raw_scores,
        training_mean=vectors.mean(axis=0),
        training_std=vectors.std(axis=0),
        population_size=len(features_list),
    )


def score_anomaly(model: AnomalyModel, features: RiskFeatures) -> Tuple[Optional[float], Dict]:
    """
    Returns (score, evidence). score is 0.0-1.0, where 1.0 means "more
    anomalous than every account in the training population" -- computed as
    this account's percentile rank (inverted) within the training population's
    raw decision_function scores, NOT the raw decision_function value itself
    (which has no fixed scale and isn't comparable across different fitted
    models/datasets).

    Returns (None, {"reason": ...}) if the model's training population was
    too small for a percentile rank to mean anything.
    """
    if model.population_size < MIN_POPULATION_SIZE:
        return None, {
            "reason": (
                f"Anomaly model was trained on only {model.population_size} accounts "
                f"(minimum {MIN_POPULATION_SIZE} required) -- score withheld rather than "
                f"reported as if it were meaningful."
            )
        }

    vector = np.array([features_to_vector(features)])
    scaled = model.scaler.transform(vector)
    raw_score = model.forest.decision_function(scaled)[0]

    # Percentile rank, inverted: fraction of the training population that is
    # MORE normal (higher raw_score) than this account.
    percentile_more_normal = float((model.training_raw_scores > raw_score).mean())
    anomaly_score = round(percentile_more_normal, 4)

    # Explainability: Isolation Forest gives no native per-feature attribution.
    # Report the top few features furthest (in z-score terms) from the
    # training population's mean -- defensible, not SHAP-level rigor, and
    # honestly labeled as such.
    z_scores = np.abs((vector[0] - model.training_mean) / np.where(model.training_std == 0, 1, model.training_std))
    top_indices = np.argsort(z_scores)[::-1][:3]
    top_features = [
        {"feature": FEATURE_NAMES[i], "value": float(vector[0][i]), "z_score": round(float(z_scores[i]), 2)}
        for i in top_indices
        if z_scores[i] > 1.0  # only report features that are actually unusual
    ]

    return anomaly_score, {
        "population_size": model.population_size,
        "top_contributing_features": top_features,
    }