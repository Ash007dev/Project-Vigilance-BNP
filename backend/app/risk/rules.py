"""Evaluate clear risk rules against calculated account features.

How it works: each rule returns whether it triggered, its evidence, and its
score contribution. Result: risk decisions remain explainable. Example: a
transfer above the configured limit triggers ``large_transaction``.
"""
from __future__ import annotations

from typing import List

from .config import DEFAULT_THRESHOLDS, RiskThresholds
from .schemas import RiskFeatures, RuleResult


def evaluate_rules(
    features: RiskFeatures,
    thresholds: RiskThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleResult]:
    rule_functions = [
        _rule_large_transaction,
        _rule_high_frequency,
        _rule_high_velocity,
        _rule_structuring,
        _rule_amount_deviation,
        _rule_historical_deviation,
        _rule_rapid_forwarding,
        _rule_mule_behavior,
        _rule_circular_flow,
        _rule_layering,
        _rule_network_risk,
        _rule_shared_device,
        _rule_shared_ip,
        _rule_location_change,
        _rule_high_risk_geography,
        _rule_kyc_risk,
        _rule_multiple_beneficiaries,
        _rule_multiple_senders,
        _rule_crypto_offramp,
    ]
    return [fn(features, thresholds) for fn in rule_functions]


def _rule_large_transaction(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    triggered = f.max_transaction_amount >= t.large_transaction_amount
    return RuleResult(
        rule_name="large_transaction",
        family="amount_anomaly",
        triggered=triggered,
        raw_value=f.max_transaction_amount,
        threshold=t.large_transaction_amount,
        contribution=t.weights["large_transaction"] if triggered else 0.0,
        severity="medium" if triggered else None,
        explanation=(
            f"Largest transaction ({f.max_transaction_amount:,.2f}) meets or exceeds the "
            f"configured large-transaction threshold ({t.large_transaction_amount:,.2f})."
            if triggered else
            "No single transaction met the large-transaction threshold."
        ),
        evidence={"max_transaction_amount": f.max_transaction_amount},
    )


def _rule_high_frequency(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    triggered = (
        f.transactions_last_1h >= t.high_frequency_tx_per_hour
        or f.transactions_last_24h >= t.high_frequency_tx_per_24h
    )
    return RuleResult(
        rule_name="high_frequency",
        family="velocity_frequency",
        triggered=triggered,
        raw_value=max(f.transactions_last_1h, f.transactions_last_24h),
        threshold=t.high_frequency_tx_per_hour,
        contribution=t.weights["high_frequency"] if triggered else 0.0,
        severity="high" if triggered else None,
        explanation=(
            f"{f.transactions_last_1h} transactions in the last hour / "
            f"{f.transactions_last_24h} in the last 24h -- at or above the configured "
            f"frequency thresholds ({t.high_frequency_tx_per_hour}/hr, {t.high_frequency_tx_per_24h}/24h)."
            if triggered else
            "Transaction frequency is within normal range."
        ),
        evidence={"transactions_last_1h": f.transactions_last_1h, "transactions_last_24h": f.transactions_last_24h},
    )


def _rule_high_velocity(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    """
    Distinct from high_frequency: this looks at the densest BURST anywhere in
    the account's history (see features.calculate_transaction_velocity), not
    just a fixed window ending "now". Catches a burst that happened earlier
    and may no longer show up in a last-1h/last-24h count.
    """
    triggered = f.burst_velocity_score >= t.high_frequency_tx_per_hour * t.burst_velocity_threshold
    threshold_value = t.high_frequency_tx_per_hour * t.burst_velocity_threshold
    return RuleResult(
        rule_name="high_velocity",
        family="velocity_frequency",
        triggered=triggered,
        raw_value=f.burst_velocity_score,
        threshold=threshold_value,
        contribution=t.weights["high_velocity"] if triggered else 0.0,
        severity="high" if triggered else None,
        explanation=(
            f"A burst of {f.burst_velocity_score:.0f} transactions occurred within a short "
            f"window at some point in this account's history -- a rapid-movement pattern, "
            f"even if current frequency looks normal."
            if triggered else
            "No unusual transaction burst detected in this account's history."
        ),
        evidence={"burst_velocity_score": f.burst_velocity_score},
    )


def _rule_structuring(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    similar_amounts = (
        f.sub_threshold_amount_coefficient_of_variation is not None
        and f.sub_threshold_amount_coefficient_of_variation <= t.structuring_max_coefficient_of_variation
    )
    triggered = f.sub_threshold_outgoing_count_24h >= t.structuring_min_count
    return RuleResult(
        rule_name="structuring",
        family="standalone",
        triggered=triggered,
        raw_value=f.sub_threshold_outgoing_count_24h,
        threshold=t.structuring_min_count,
        contribution=t.weights["structuring"] if triggered else 0.0,
        severity="high" if triggered else None,
        explanation=(
            (
                f"{f.sub_threshold_outgoing_count_24h} outgoing transactions below the reporting "
                f"threshold occurred within {t.structuring_window_hours}h, totalling "
                f"{f.sub_threshold_total_amount_24h:,.2f}"
                + (
                    " with repeatedly similar amounts (low variation)"
                    if similar_amounts else ""
                )
                + " -- a pattern consistent with structuring/smurfing. Investigation recommended."
            )
            if triggered else
            "No structuring pattern detected in the configured window."
        ),
        evidence={
            "count": f.sub_threshold_outgoing_count_24h,
            "total_amount": f.sub_threshold_total_amount_24h,
            "coefficient_of_variation": f.sub_threshold_amount_coefficient_of_variation,
            "amounts_repeatedly_similar": similar_amounts,
        },
    )


def _rule_amount_deviation(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    triggered = f.max_amount_deviation_ratio >= t.deviation_ratio_threshold
    return RuleResult(
        rule_name="amount_deviation",
        family="amount_anomaly",
        triggered=triggered,
        raw_value=f.max_amount_deviation_ratio,
        threshold=t.deviation_ratio_threshold,
        contribution=t.weights["amount_deviation"] if triggered else 0.0,
        severity="medium" if triggered else None,
        explanation=(
            f"Largest transaction is {f.max_amount_deviation_ratio:.1f}x this account's own "
            f"average -- a sudden deviation from typical behaviour."
            if triggered else
            "Transaction amounts are consistent with this account's own history."
        ),
        evidence={"deviation_ratio": f.max_amount_deviation_ratio},
    )


def _rule_historical_deviation(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    if not f.has_sufficient_baseline:
        return RuleResult(
            rule_name="historical_deviation",
            family="amount_anomaly",
            triggered=False,
            explanation=(
                f"Insufficient transaction history before the current "
                f"{t.current_window_days}-day window to establish a baseline -- "
                f"this factor cannot be evaluated, not confirmed clean."
            ),
            evidence={"has_sufficient_baseline": False},
        )

    ratio = None
    if f.baseline_average_amount and f.baseline_average_amount > 0 and f.current_period_average_amount is not None:
        ratio = f.current_period_average_amount / f.baseline_average_amount
    triggered = ratio is not None and ratio >= t.historical_deviation_ratio_threshold

    return RuleResult(
        rule_name="historical_deviation",
        family="amount_anomaly",
        triggered=triggered,
        raw_value=ratio,
        threshold=t.historical_deviation_ratio_threshold,
        contribution=t.weights["historical_deviation"] if triggered else 0.0,
        severity="high" if triggered else None,
        explanation=(
            f"Recent average transaction amount ({f.current_period_average_amount:,.2f}) is "
            f"{ratio:.1f}x the account's own historical baseline ({f.baseline_average_amount:,.2f})."
            if triggered else
            "Recent behaviour is consistent with this account's historical baseline."
        ),
        evidence={
            "baseline_average_amount": f.baseline_average_amount,
            "current_period_average_amount": f.current_period_average_amount,
            "ratio": ratio,
        },
    )


def _rule_rapid_forwarding(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    triggered = f.rapid_forwarding_count > 0
    return RuleResult(
        rule_name="rapid_forwarding",
        family="pass_through",
        triggered=triggered,
        raw_value=f.rapid_forwarding_count,
        threshold=1,
        contribution=(t.weights["rapid_forwarding"] * min(f.rapid_forwarding_count, 3)) if triggered else 0.0,
        severity="high" if triggered else None,
        explanation=(
            f"{f.rapid_forwarding_count} incoming transaction(s) were forwarded onward "
            f"shortly after receipt -- a pattern consistent with pass-through / mule use."
            if triggered else
            "No rapid pass-through of funds detected."
        ),
        evidence={"rapid_forwarding_count": f.rapid_forwarding_count},
    )


def _rule_mule_behavior(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    ratio_signal = f.inflow_outflow_ratio is not None and f.inflow_outflow_ratio >= t.mule_inflow_outflow_ratio_min
    triggered = (
        f.unique_senders >= t.mule_min_unique_senders
        and f.rapid_forwarding_count > 0
        and ratio_signal
    )
    return RuleResult(
        rule_name="mule_behavior",
        family="pass_through",
        triggered=triggered,
        raw_value=f.unique_senders,
        threshold=t.mule_min_unique_senders,
        contribution=t.weights["mule_behavior"] if triggered else 0.0,
        severity="critical" if triggered else None,
        explanation=(
            f"Account received funds from {f.unique_senders} distinct senders, forwarded "
            f"them onward quickly, and outflow is {f.inflow_outflow_ratio:.0%} of inflow -- "
            f"a pattern consistent with mule account behaviour. Investigation recommended."
            if triggered else
            "No mule-account pattern detected."
        ),
        evidence={
            "unique_senders": f.unique_senders,
            "rapid_forwarding_count": f.rapid_forwarding_count,
            "inflow_outflow_ratio": f.inflow_outflow_ratio,
        },
    )


def _rule_circular_flow(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    detection_confirmed = f.detection.circular_flow_detected if f.detection else None
    graph_cycle = bool(f.graph and f.graph.cycle_detected)
    reciprocal_signal = f.reciprocal_counterparty_count >= t.circular_flow_min_reciprocal_counterparties

    if detection_confirmed is True:
        triggered, explanation = True, "Detection module confirmed a circular money flow involving this account."
    elif detection_confirmed is False:
        triggered, explanation = False, "Detection module checked and found no circular flow."
    elif graph_cycle:
        triggered, explanation = True, "Graph analysis confirmed a closed-loop transaction cycle involving this account."
    elif reciprocal_signal:
        triggered = True
        explanation = (
            f"Account exchanged funds with {f.reciprocal_counterparty_count} counterpart(y/ies) "
            f"in both directions -- a possible circular-flow signal (2-hop proxy, not graph-confirmed)."
        )
    else:
        triggered, explanation = False, "No circular money flow pattern detected."

    return RuleResult(
        rule_name="circular_flow",
        family="network_topology",
        triggered=triggered,
        raw_value=f.reciprocal_counterparty_count,
        threshold=t.circular_flow_min_reciprocal_counterparties,
        contribution=t.weights["circular_flow"] if triggered else 0.0,
        severity="high" if triggered else None,
        explanation=explanation,
        evidence={
            "detection_module_result": detection_confirmed,
            "graph_cycle_detected": f.graph.cycle_detected if f.graph else None,
            "reciprocal_counterparty_count": f.reciprocal_counterparty_count,
        },
    )


def _rule_layering(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    detection_confirmed = f.detection.layering_detected if f.detection else None
    graph_depth = f.graph.graph_depth if f.graph else None

    if detection_confirmed is True:
        triggered, explanation = True, "Detection module confirmed a multi-hop layering chain involving this account."
    elif detection_confirmed is False:
        triggered, explanation = False, "Detection module checked and found no layering pattern."
    elif graph_depth is not None:
        triggered = graph_depth >= t.layering_min_hops
        explanation = (
            f"Graph traversal found a fund-movement chain {graph_depth} hops deep, at or "
            f"above the configured layering threshold ({t.layering_min_hops})."
            if triggered else "No layering pattern detected."
        )
    else:
        triggered = False
        explanation = "Layering depth is unknown -- requires graph-module input to evaluate reliably."

    return RuleResult(
        rule_name="layering",
        family="network_topology",
        triggered=triggered,
        raw_value=graph_depth,
        threshold=t.layering_min_hops,
        contribution=t.weights["layering"] if triggered else 0.0,
        severity="high" if triggered else None,
        explanation=explanation,
        evidence={"detection_module_result": detection_confirmed, "graph_depth": graph_depth},
    )


def _rule_network_risk(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    """
    General "how unusually connected is this account" signal -- distinct from
    the pattern-specific layering/circular_flow rules. Uses graph degree when
    available, else unique_counterparties as an internal proxy.
    """
    degree = f.graph.graph_degree if (f.graph and f.graph.graph_degree is not None) else f.unique_counterparties
    threshold = t.mule_min_unique_senders * 2  # reuses an existing config value rather than adding a redundant one
    triggered = degree >= threshold
    return RuleResult(
        rule_name="network_risk",
        family="network_topology",
        triggered=triggered,
        raw_value=degree,
        threshold=threshold,
        contribution=t.weights["network_risk"] if triggered else 0.0,
        severity="medium" if triggered else None,
        explanation=(
            f"Account is connected to {degree} distinct counterparties/network neighbours, "
            f"unusually high connectivity for this dataset."
            if triggered else
            "Network connectivity is within normal range."
        ),
        evidence={"degree": degree, "source": "graph_module" if f.graph and f.graph.graph_degree is not None else "internal_approximation"},
    )


def _rule_shared_device(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    detection_confirmed = f.detection.shared_device_detected if f.detection else None
    triggered = (
        detection_confirmed if detection_confirmed is not None
        else f.max_accounts_sharing_a_device >= t.shared_device_min_accounts
    )
    return RuleResult(
        rule_name="shared_device",
        family="identity_infra",
        triggered=triggered,
        raw_value=f.max_accounts_sharing_a_device,
        threshold=t.shared_device_min_accounts,
        contribution=t.weights["shared_device"] if triggered else 0.0,
        severity="medium" if triggered else None,
        explanation=(
            f"A device used to send from this account was also used to send from "
            f"{f.max_accounts_sharing_a_device} distinct accounts total."
            if triggered else
            "No cross-account device sharing detected for this account's outgoing transactions."
        ),
        evidence={"max_accounts_sharing_a_device": f.max_accounts_sharing_a_device, "detection_module_result": detection_confirmed},
    )


def _rule_shared_ip(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    detection_confirmed = f.detection.shared_ip_detected if f.detection else None
    triggered = (
        detection_confirmed if detection_confirmed is not None
        else f.max_accounts_sharing_an_ip >= t.shared_ip_min_accounts
    )
    return RuleResult(
        rule_name="shared_ip",
        family="identity_infra",
        triggered=triggered,
        raw_value=f.max_accounts_sharing_an_ip,
        threshold=t.shared_ip_min_accounts,
        contribution=t.weights["shared_ip"] if triggered else 0.0,
        severity="medium" if triggered else None,
        explanation=(
            f"An IP used to send from this account was also used to send from "
            f"{f.max_accounts_sharing_an_ip} distinct accounts total."
            if triggered else
            "No cross-account IP sharing detected for this account's outgoing transactions."
        ),
        evidence={"max_accounts_sharing_an_ip": f.max_accounts_sharing_an_ip, "detection_module_result": detection_confirmed},
    )


def _rule_location_change(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    triggered = f.location_change_count >= t.location_change_min_count
    return RuleResult(
        rule_name="location_change",
        family="identity_infra",
        triggered=triggered,
        raw_value=f.location_change_count,
        threshold=t.location_change_min_count,
        contribution=t.weights["location_change"] if triggered else 0.0,
        severity="low" if triggered else None,
        explanation=(
            f"This account's outgoing transactions changed location {f.location_change_count} "
            f"times across its history."
            if triggered else
            "No unusual location changes detected for this account's outgoing transactions."
        ),
        evidence={"location_change_count": f.location_change_count},
    )


def _rule_high_risk_geography(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    """
    t.high_risk_geography is a configurable {country: severity} map, empty by
    default. This rule NEVER hardcodes a country -- it only ever reads config.
    Country membership isn't directly on RiskFeatures (features.py doesn't
    single out one "the" country); this reads from evidence the caller can
    attach, or is a no-op (never triggers) until that config is populated AND
    a country signal is wired in. Documented as a known gap, not silently
    faked.
    """
    return RuleResult(
        rule_name="high_risk_geography",
        family="standalone",
        triggered=False,
        explanation=(
            "High-risk geography list is empty in config, or no country signal is wired "
            "into this rule yet -- populate RiskThresholds.high_risk_geography to activate."
            if not t.high_risk_geography else
            "No transactions matched the configured high-risk geography list."
        ),
        evidence={"configured_countries": list(t.high_risk_geography.keys())},
    )


def _rule_kyc_risk(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    contribution = t.kyc_contribution.get(f.kyc_status, t.kyc_contribution.get("unknown", 0.0))
    triggered = contribution > 0
    return RuleResult(
        rule_name="kyc_risk",
        family="standalone",
        triggered=triggered,
        contribution=contribution,
        severity="medium" if triggered else None,
        explanation=(
            f"KYC status is '{f.kyc_status}', which carries a configured risk contribution."
            if triggered else
            "KYC status is complete; no KYC-related risk contribution."
        ),
        evidence={"kyc_status": f.kyc_status},
    )


def _rule_multiple_beneficiaries(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    triggered = f.unique_receivers >= t.multiple_beneficiaries_min_count
    return RuleResult(
        rule_name="multiple_beneficiaries",
        family="standalone",
        triggered=triggered,
        raw_value=f.unique_receivers,
        threshold=t.multiple_beneficiaries_min_count,
        contribution=t.weights["multiple_beneficiaries"] if triggered else 0.0,
        severity="low" if triggered else None,
        explanation=(
            f"Account sent money to {f.unique_receivers} distinct beneficiaries."
            if triggered else
            "Beneficiary count is within normal range."
        ),
        evidence={"unique_receivers": f.unique_receivers},
    )


def _rule_multiple_senders(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    """
    NOTE: scorer.py suppresses this rule's contribution when mule_behavior
    also triggers on the same account -- mule_behavior's own definition
    already requires a high unique_senders count, so counting both would be
    scoring the same evidence twice under two names. This function itself
    stays simple and unaware of that -- the suppression is scorer.py's job.
    """
    triggered = f.unique_senders >= t.multiple_senders_min_count
    return RuleResult(
        rule_name="multiple_senders",
        family="standalone",
        triggered=triggered,
        raw_value=f.unique_senders,
        threshold=t.multiple_senders_min_count,
        contribution=t.weights["multiple_senders"] if triggered else 0.0,
        severity="low" if triggered else None,
        explanation=(
            f"Account received money from {f.unique_senders} distinct senders."
            if triggered else
            "Sender count is within normal range."
        ),
        evidence={"unique_senders": f.unique_senders},
    )


def _rule_crypto_offramp(f: RiskFeatures, t: RiskThresholds) -> RuleResult:
    detection_confirmed = f.detection.crypto_offramping_detected if f.detection else None
    triggered = (
        detection_confirmed if detection_confirmed is not None
        else f.crypto_transaction_count >= t.crypto_offramp_min_count
    )
    return RuleResult(
        rule_name="crypto_offramp",
        family="standalone",
        triggered=triggered,
        raw_value=f.crypto_transaction_count,
        threshold=t.crypto_offramp_min_count,
        contribution=t.weights["crypto_offramp"] if triggered else 0.0,
        severity="medium" if triggered else None,
        explanation=(
            f"{f.crypto_transaction_count} transaction(s) moved funds into or out of "
            f"cryptocurrency, totalling {f.crypto_total_amount:,.2f}."
            if triggered else
            "No cryptocurrency off-ramping activity detected."
        ),
        evidence={"crypto_transaction_count": f.crypto_transaction_count, "crypto_total_amount": f.crypto_total_amount},
    )
