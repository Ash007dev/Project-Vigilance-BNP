"""Compare account behaviour with an Isolation Forest model.

How it works: train once on a population of account features, then convert
each model result into an anomaly percentile. Result: unusual accounts add a
second signal beside deterministic rules. Example: an account with an extreme
transaction rate can receive a high anomaly score.
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
