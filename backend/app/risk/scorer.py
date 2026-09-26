"""Combine rule contributions and an optional anomaly score.

How it works: related rules are grouped to avoid counting the same evidence
twice, then the rule and model channels are blended into 0-100. Result: one
stable and explainable risk assessment. Example: a large transaction and its
amount deviation count as one amount-anomaly family.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from .config import DEFAULT_THRESHOLDS, RiskThresholds
from .schemas import RiskAssessment, RiskFeatures, RuleResult

_MAX_COMBINE_FAMILIES = {"amount_anomaly", "velocity_frequency", "pass_through"}
_SUM_CAPPED_FAMILIES = {"network_topology", "identity_infra"}
# everything else is treated as "standalone" (summed, no cap)

# For families where "max by contribution" isn't the right tie-break: some
# rules scale their contribution with a count (e.g. rapid_forwarding can hit
# 3x its base weight), which can numerically exceed a flat-weight rule that
# is actually the more specific, confirmed finding. mule_behavior is a
# superset of rapid_forwarding's evidence and must win regardless of which
# raw number is bigger -- a real bug caught during testing when
# rapid_forwarding's scaled contribution (45) beat mule_behavior's flat
# weight (20), silently discarding the more severe, more specific rule.
_FAMILY_PRIORITY_WINNER = {
    "pass_through": "mule_behavior",
}


def calculate_theoretical_max_rule_score(thresholds: RiskThresholds = DEFAULT_THRESHOLDS) -> float:
    """
    The rule_score a hypothetical account would get if EVERY rule triggered,
    after family combination -- used to rescale the actual total to 0-100.
    Computed from config, not hardcoded, so changing weights/caps in config.py
    automatically keeps this correct.
    """
    w = thresholds.weights

    amount_anomaly_max = max(w["large_transaction"], w["amount_deviation"], w["historical_deviation"])
    velocity_max = max(w["high_frequency"], w["high_velocity"])
    pass_through_max = max(w["rapid_forwarding"] * 3, w["mule_behavior"])  # rapid_forwarding scales up to x3

    network_topology_sum = w["layering"] + w["circular_flow"] + w["network_risk"]
    network_topology_capped = min(network_topology_sum, thresholds.family_caps["network_topology"])

    identity_infra_sum = w["shared_device"] + w["shared_ip"] + w["location_change"]
    identity_infra_capped = min(identity_infra_sum, thresholds.family_caps["identity_infra"])

    standalone_sum = (
        w["structuring"] + w["high_risk_geography"] + max(thresholds.kyc_contribution.values())
        + w["crypto_offramp"] + w["multiple_beneficiaries"] + w["multiple_senders"]
    )

    return (
        amount_anomaly_max + velocity_max + pass_through_max
        + network_topology_capped + identity_infra_capped + standalone_sum
    )


def _apply_family_rules(rule_results: List[RuleResult], thresholds: RiskThresholds) -> List[RuleResult]:
    """
    Returns a NEW list of RuleResult where .contribution reflects what
    actually counts toward the score after family combination and
    supersession -- the originals from evaluate_rules() are never mutated.
    triggered flags are left alone (the underlying evidence is still real);
    only contribution changes.
    """
    by_family: Dict[str, List[RuleResult]] = {}
    for r in rule_results:
        by_family.setdefault(r.family, []).append(r)

    adjusted: List[RuleResult] = []

    for family, members in by_family.items():
        triggered_members = [m for m in members if m.triggered]

        if family in _MAX_COMBINE_FAMILIES:
            if not triggered_members:
                adjusted.extend(members)
                continue

            priority_name = _FAMILY_PRIORITY_WINNER.get(family)
            priority_member = next((m for m in triggered_members if m.rule_name == priority_name), None)
            winner = priority_member if priority_member is not None else max(triggered_members, key=lambda m: m.contribution)

            for m in members:
                if m is winner:
                    adjusted.append(m)
                elif m.triggered:
                    adjusted.append(m.model_copy(update={
                        "contribution": 0.0,
                        "evidence": {**m.evidence, "note": f"not double-counted: family '{family}' uses max; '{winner.rule_name}' scored higher"},
                    }))
                else:
                    adjusted.append(m)

        elif family in _SUM_CAPPED_FAMILIES:
            total = sum(m.contribution for m in triggered_members)
            cap = thresholds.family_caps.get(family, total)
            if total <= cap or total == 0:
                adjusted.extend(members)
            else:
                scale = cap / total
                for m in members:
                    if m.triggered:
                        adjusted.append(m.model_copy(update={
                            "contribution": m.contribution * scale,
                            "evidence": {**m.evidence, "note": f"scaled down: family '{family}' total capped at {cap}"},
                        }))
                    else:
                        adjusted.append(m)
        else:
            adjusted.extend(members)

    # Supersession: mule_behavior triggering zeroes out multiple_senders' contribution.
    mule = next((r for r in adjusted if r.rule_name == "mule_behavior"), None)
    if mule and mule.triggered:
        for i, r in enumerate(adjusted):
            if r.rule_name == "multiple_senders" and r.triggered and r.contribution > 0:
                adjusted[i] = r.model_copy(update={
                    "contribution": 0.0,
                    "evidence": {**r.evidence, "note": "not double-counted: superseded by mule_behavior, which already reflects high unique_senders"},
                })

    return adjusted


def calculate_risk(
    features: RiskFeatures,
    rule_results: List[RuleResult],
    ml_anomaly_score: Optional[float] = None,
    thresholds: RiskThresholds = DEFAULT_THRESHOLDS,
) -> RiskAssessment:
    """
    ml_anomaly_score is 0.0-1.0 (from model.score_anomaly) or None if no
    anomaly model was run / population was too small. Pass None explicitly
    rather than 0.0 when you don't have a real score -- 0.0 would falsely
    claim "confirmed not anomalous".
    """
    adjusted_rules = _apply_family_rules(rule_results, thresholds)

    raw_rule_total = sum(r.contribution for r in adjusted_rules if r.triggered)
    theoretical_max = calculate_theoretical_max_rule_score(thresholds)
    rule_score = min(100.0, (raw_rule_total / theoretical_max) * 100) if theoretical_max > 0 else 0.0

    if ml_anomaly_score is not None:
        ml_score = ml_anomaly_score * 100
        blended = thresholds.rule_channel_weight * rule_score + thresholds.ml_channel_weight * ml_score
    else:
        blended = rule_score  # 100% rule channel when no ML signal is available

    clamped_score = int(max(thresholds.min_score, min(thresholds.max_score, round(blended))))
    risk_level = _classify(clamped_score, thresholds)

    triggered_for_output = [r for r in adjusted_rules if r.triggered]
    reasons = [r.explanation for r in triggered_for_output if r.contribution > 0 or r.rule_name == "mule_behavior"]
    if ml_anomaly_score is not None and ml_anomaly_score > 0.5:
        reasons.append(
            f"Behavioural anomaly model rated this account more unusual than "
            f"{ml_anomaly_score:.0%} of the comparison population."
        )
    if not reasons:
        reasons.append("No risk indicators triggered for this account in the analysed window.")

    return RiskAssessment(
        account_id=features.account_id,
        risk_score=clamped_score,
        risk_level=risk_level,
        rule_score=round(rule_score, 2),
        ml_anomaly_score=ml_anomaly_score,
        triggered_rules=triggered_for_output,
        reasons=reasons,
        feature_summary=features.model_dump(exclude={"graph", "detection"}),
        generated_at=datetime.now(timezone.utc),
    )


def _classify(score: int, t: RiskThresholds) -> str:
    if score <= t.low_max:
        return "Low"
    if score <= t.medium_max:
        return "Medium"
    if score <= t.high_max:
        return "High"
    return "Critical"
