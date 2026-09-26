"""Calculate account behaviour features from normalized transactions.

How it works: group incoming and outgoing rows, then measure amounts, speed,
counterparties, devices, locations, and history. Result: rules receive one
consistent feature model. Example: repeated outgoing transfers increase the
24-hour transaction count.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from .config import DEFAULT_THRESHOLDS, RiskThresholds
from .schemas import (
    CustomerData,
    DetectionSignals,
    GraphMetrics,
    RiskFeatures,
    TransactionInput,
)

_COLUMNS = [
    "transaction_id", "timestamp", "sender_account", "receiver_account",
    "sender_customer_id", "receiver_customer_id",
    "amount", "currency", "channel", "ip_address", "device_id",
    "location_country", "location_city", "is_crypto", "crypto_wallet",
]


# ============================================================================
# Normalization
# ============================================================================

def _to_dataframe(transactions: Iterable[TransactionInput]) -> pd.DataFrame:
    records = [t.model_dump() for t in transactions]
    df = pd.DataFrame.from_records(records, columns=_COLUMNS)
    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df.loc[df["amount"] < 0, "amount"] = np.nan  # defense-in-depth; pydantic already rejects these

    df.drop_duplicates(subset=["transaction_id"], keep="first", inplace=True)
    df["is_crypto"] = df["is_crypto"].fillna(False).astype(bool)
    return df


def _to_long_format(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (transaction, role) -- lets a single groupby("account_id")
    answer both "as sender" and "as receiver" questions at once."""
    outgoing = df.dropna(subset=["sender_account"]).copy()
    outgoing["account_id"] = outgoing["sender_account"]
    outgoing["direction"] = "out"

    incoming = df.dropna(subset=["receiver_account"]).copy()
    incoming["account_id"] = incoming["receiver_account"]
    incoming["direction"] = "in"

    return pd.concat([outgoing, incoming], ignore_index=True)


# ============================================================================
# Cross-account infrastructure sharing (needs the FULL dataset, not one account)
# ============================================================================

def build_shared_infrastructure_maps(
    transactions: Iterable[TransactionInput],
) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """
    Scans the whole transaction set once and returns:
      device_id -> set of distinct accounts (sender or receiver) seen using it
      ip_address -> set of distinct accounts seen using it

    Build this ONCE per dataset/batch and reuse it -- don't rebuild per account.
    """
    device_to_accounts: Dict[str, Set[str]] = {}
    ip_to_accounts: Dict[str, Set[str]] = {}

    for t in transactions:
        # Only the SENDER initiated the transaction from this device/IP. The
        # receiver's own device/IP isn't recorded in this schema, and
        # attributing the sender's device to the receiver was a real bug
        # caught during testing: it inflated shared-device counts by
        # pulling in every receiver that ever got paid by a shared device,
        # which has nothing to do with the actual fraud pattern (one device
        # controlling multiple SENDING accounts).
        if not t.sender_account:
            continue
        if t.device_id:
            device_to_accounts.setdefault(t.device_id, set()).add(t.sender_account)
        if t.ip_address:
            ip_to_accounts.setdefault(t.ip_address, set()).add(t.sender_account)

    return device_to_accounts, ip_to_accounts


def calculate_shared_device_count(
    account_device_ids: Set[str],
    device_to_accounts: Dict[str, Set[str]],
) -> int:
    """Max number of distinct accounts sharing ANY ONE device this account used."""
    if not account_device_ids:
        return 0
    counts = [len(device_to_accounts.get(d, set())) for d in account_device_ids]
    return max(counts) if counts else 0


def calculate_shared_ip_count(
    account_ip_addresses: Set[str],
    ip_to_accounts: Dict[str, Set[str]],
) -> int:
    """Max number of distinct accounts sharing ANY ONE IP this account used."""
    if not account_ip_addresses:
        return 0
    counts = [len(ip_to_accounts.get(ip, set())) for ip in account_ip_addresses]
    return max(counts) if counts else 0


# ============================================================================
# Independently-testable calculate_* functions
# All operate on a "group": a DataFrame of one account's rows, long-format
# (has an "account_id" and "direction" column), plus the account_id itself.
# ============================================================================

def calculate_transaction_frequency(group: pd.DataFrame, reference_time: pd.Timestamp, window_hours: int) -> int:
    """Count of transactions (any direction) within `window_hours` before reference_time."""
    if group.empty:
        return 0
    window_start = reference_time - pd.Timedelta(hours=window_hours)
    return int((group["timestamp"] >= window_start).sum())


def calculate_transaction_velocity(group: pd.DataFrame, burst_window_minutes: int) -> float:
    """
    Max number of transactions found in ANY rolling `burst_window_minutes`
    window across the account's whole history -- distinct from frequency,
    which only looks at a fixed window ending at reference_time. This catches
    a burst that happened at any point, not just "recently".

    Returns the raw max count (not yet compared to a threshold -- that's rules.py).
    """
    if group.empty or len(group) < 2:
        return float(len(group))

    times = group["timestamp"].sort_values().to_numpy(dtype="datetime64[ns]").astype("int64")
    window_ns = int(pd.Timedelta(minutes=burst_window_minutes).value)

    max_count = 1
    left = 0
    for right in range(len(times)):
        while times[right] - times[left] > window_ns:
            left += 1
        max_count = max(max_count, right - left + 1)
    return float(max_count)


def calculate_average_amount(group: pd.DataFrame) -> float:
    amounts = group["amount"].dropna()
    return float(amounts.mean()) if not amounts.empty else 0.0


def calculate_median_amount(group: pd.DataFrame) -> float:
    amounts = group["amount"].dropna()
    return float(amounts.median()) if not amounts.empty else 0.0


def calculate_max_amount(group: pd.DataFrame) -> float:
    amounts = group["amount"].dropna()
    return float(amounts.max()) if not amounts.empty else 0.0


def calculate_min_amount(group: pd.DataFrame) -> float:
    amounts = group["amount"].dropna()
    return float(amounts.min()) if not amounts.empty else 0.0


def calculate_amount_deviation(group: pd.DataFrame) -> float:
    """(max - mean) / mean, i.e. how many multiples of the average the largest transaction is."""
    avg = calculate_average_amount(group)
    mx = calculate_max_amount(group)
    return ((mx - avg) / avg) if avg > 0 else 0.0


def calculate_unique_beneficiaries(group: pd.DataFrame) -> int:
    outgoing = group[group["direction"] == "out"]
    return int(outgoing["receiver_account"].nunique(dropna=True))


def calculate_unique_senders(group: pd.DataFrame) -> int:
    incoming = group[group["direction"] == "in"]
    return int(incoming["sender_account"].nunique(dropna=True))


def calculate_location_changes(group: pd.DataFrame) -> int:
    """Count of chronological transitions between different location_country values."""
    ordered = group.sort_values("timestamp")
    countries = ordered["location_country"].dropna()
    if len(countries) < 2:
        return 0
    return int((countries != countries.shift()).sum() - 1)  # first row isn't a "change"


def calculate_rapid_forwarding(
    incoming: pd.DataFrame,
    outgoing: pd.DataFrame,
    window_minutes: int,
    amount_ratio: float,
) -> int:
    """
    For each incoming transaction, was there an outgoing transaction within
    `window_minutes` afterward moving at least `amount_ratio` of it back out?
    Uses np.searchsorted, not a per-row DataFrame mask -- see the perf note
    in the git history of this file (an earlier boolean-mask version took
    ~40s for 120k transactions across 2,000 accounts; this does not).
    """
    if incoming.empty or outgoing.empty:
        return 0

    out_sorted = outgoing.sort_values("timestamp")
    out_times_ns = out_sorted["timestamp"].to_numpy(dtype="datetime64[ns]").astype("int64")
    out_amounts = out_sorted["amount"].to_numpy()
    window_ns = int(pd.Timedelta(minutes=window_minutes).value)

    in_times_ns = incoming["timestamp"].to_numpy(dtype="datetime64[ns]").astype("int64")
    in_amounts = incoming["amount"].to_numpy()

    count = 0
    for in_time_ns, in_amount in zip(in_times_ns, in_amounts):
        if pd.isna(in_amount) or in_amount <= 0:
            continue
        lo = np.searchsorted(out_times_ns, in_time_ns, side="left")
        hi = np.searchsorted(out_times_ns, in_time_ns + window_ns, side="right")
        if lo >= hi:
            continue
        window_max = out_amounts[lo:hi].max()
        if not np.isnan(window_max) and window_max >= in_amount * amount_ratio:
            count += 1
    return count


def calculate_inflow_outflow_ratio(group: pd.DataFrame) -> Optional[float]:
    incoming_total = group.loc[group["direction"] == "in", "amount"].dropna().sum()
    outgoing_total = group.loc[group["direction"] == "out", "amount"].dropna().sum()
    if incoming_total <= 0:
        return None
    return float(outgoing_total / incoming_total)


def calculate_structuring_signal(
    outgoing: pd.DataFrame,
    reference_time: pd.Timestamp,
    window_hours: int,
    amount_threshold: float,
) -> Tuple[int, Optional[float], float]:
    """
    Returns (count, coefficient_of_variation, total_amount) for outgoing
    transactions below `amount_threshold` within `window_hours` of reference_time.

    coefficient_of_variation (std/mean) is low when amounts are repeatedly
    similar -- the "repeated similar amounts" signal your brief asked for,
    distinct from just counting sub-threshold transactions.
    """
    window_start = reference_time - pd.Timedelta(hours=window_hours)
    candidates = outgoing[
        (outgoing["amount"] < amount_threshold) & (outgoing["timestamp"] >= window_start)
    ]
    amounts = candidates["amount"].dropna()
    count = int(len(amounts))
    total = float(amounts.sum()) if count else 0.0
    cov: Optional[float] = None
    if count >= 2 and amounts.mean() > 0:
        cov = float(amounts.std(ddof=0) / amounts.mean())
    return count, cov, total


@dataclass
class HistoricalBaseline:
    has_sufficient_baseline: bool
    baseline_average_amount: Optional[float]
    baseline_transactions_per_day: Optional[float]
    baseline_unique_beneficiaries: Optional[int]
    current_period_average_amount: Optional[float]
    current_period_transactions_per_day: Optional[float]
    current_period_unique_beneficiaries: Optional[int]


def calculate_historical_baseline(
    group: pd.DataFrame,
    reference_time: pd.Timestamp,
    baseline_days: int,
    current_days: int,
    min_baseline_transactions: int,
) -> HistoricalBaseline:
    """
    Splits the account's history into an older "baseline" period and a recent
    "current" period, both relative to reference_time. If the baseline period
    doesn't contain enough transactions, has_sufficient_baseline is False and
    every baseline_* field is None -- rules.py must treat that as "cannot
    evaluate", not as "no deviation found".
    """
    current_start = reference_time - pd.Timedelta(days=current_days)
    baseline_start = current_start - pd.Timedelta(days=baseline_days)

    baseline_rows = group[(group["timestamp"] >= baseline_start) & (group["timestamp"] < current_start)]
    current_rows = group[group["timestamp"] >= current_start]

    if len(baseline_rows) < min_baseline_transactions:
        return HistoricalBaseline(False, None, None, None, None, None, None)

    def _per_day_rate(rows: pd.DataFrame, days: int) -> float:
        return len(rows) / days if days > 0 else 0.0

    baseline_amounts = baseline_rows["amount"].dropna()
    current_amounts = current_rows["amount"].dropna()

    return HistoricalBaseline(
        has_sufficient_baseline=True,
        baseline_average_amount=float(baseline_amounts.mean()) if not baseline_amounts.empty else None,
        baseline_transactions_per_day=_per_day_rate(baseline_rows, baseline_days),
        baseline_unique_beneficiaries=int(
            baseline_rows.loc[baseline_rows["direction"] == "out", "receiver_account"].nunique(dropna=True)
        ),
        current_period_average_amount=float(current_amounts.mean()) if not current_amounts.empty else None,
        current_period_transactions_per_day=_per_day_rate(current_rows, current_days),
        current_period_unique_beneficiaries=int(
            current_rows.loc[current_rows["direction"] == "out", "receiver_account"].nunique(dropna=True)
        ),
    )


# ============================================================================
# Orchestration -- the ONE place that assembles a RiskFeatures object
# ============================================================================

def _compute_features_for_account(
    account_id: str,
    group: pd.DataFrame,
    reference_time: pd.Timestamp,
    thresholds: RiskThresholds,
    graph_metrics: Optional[GraphMetrics],
    detection_signals: Optional[DetectionSignals],
    customer_data: Optional[CustomerData],
    device_to_accounts: Optional[Dict[str, Set[str]]],
    ip_to_accounts: Optional[Dict[str, Set[str]]],
) -> RiskFeatures:
    # reference_time may arrive as a plain datetime.datetime (e.g. round-tripped
    # from a RiskFeatures.reference_time value someone read back in) or as a
    # pd.Timestamp (the internal default path). Normalize once, here, rather
    # than assuming the caller got the type right -- an earlier version of
    # this function assumed pd.Timestamp unconditionally and crashed on a
    # plain datetime with "no attribute to_pydatetime".
    reference_time = pd.Timestamp(reference_time)

    if group.empty:
        return RiskFeatures(
            account_id=account_id,
            reference_time=reference_time.to_pydatetime(),
            kyc_status=customer_data.kyc_status if customer_data else "unknown",
            graph=graph_metrics,
            detection=detection_signals,
        )

    incoming = group[group["direction"] == "in"]
    outgoing = group[group["direction"] == "out"]

    counterparties_in = set(incoming["sender_account"].dropna())
    counterparties_out = set(outgoing["receiver_account"].dropna())

    crypto_rows = group[group["is_crypto"]]

    structuring_count, structuring_cov, structuring_total = calculate_structuring_signal(
        outgoing, reference_time, thresholds.structuring_window_hours, thresholds.structuring_amount_threshold,
    )

    baseline = calculate_historical_baseline(
        group, reference_time,
        thresholds.baseline_window_days, thresholds.current_window_days, thresholds.min_baseline_transactions,
    )

    device_ids = set(outgoing["device_id"].dropna())
    ip_addresses = set(outgoing["ip_address"].dropna())
    shared_device = (
        calculate_shared_device_count(device_ids, device_to_accounts) if device_to_accounts is not None else 0
    )
    shared_ip = (
        calculate_shared_ip_count(ip_addresses, ip_to_accounts) if ip_to_accounts is not None else 0
    )

    return RiskFeatures(
        account_id=account_id,
        customer_id=customer_data.customer_id if customer_data else None,
        reference_time=reference_time.to_pydatetime(),

        transaction_count=int(group["transaction_id"].nunique()),
        incoming_transaction_count=int(len(incoming)),
        outgoing_transaction_count=int(len(outgoing)),
        total_incoming_amount=float(incoming["amount"].dropna().sum()),
        total_outgoing_amount=float(outgoing["amount"].dropna().sum()),
        average_transaction_amount=calculate_average_amount(group),
        median_transaction_amount=calculate_median_amount(group),
        max_transaction_amount=calculate_max_amount(group),
        min_transaction_amount=calculate_min_amount(group),

        transactions_last_1h=calculate_transaction_frequency(group, reference_time, thresholds.velocity_window_1h_hours),
        transactions_last_24h=calculate_transaction_frequency(group, reference_time, thresholds.velocity_window_24h_hours),
        incoming_last_1h=calculate_transaction_frequency(incoming, reference_time, thresholds.velocity_window_1h_hours),
        outgoing_last_1h=calculate_transaction_frequency(outgoing, reference_time, thresholds.velocity_window_1h_hours),
        average_seconds_between_transactions=_avg_gap_seconds(group),
        burst_velocity_score=calculate_transaction_velocity(group, burst_window_minutes=5),

        max_amount_deviation_ratio=calculate_amount_deviation(group),

        sub_threshold_outgoing_count_24h=structuring_count,
        sub_threshold_amount_coefficient_of_variation=structuring_cov,
        sub_threshold_total_amount_24h=structuring_total,

        rapid_forwarding_count=calculate_rapid_forwarding(
            incoming, outgoing, thresholds.rapid_forwarding_window_minutes, thresholds.rapid_forwarding_amount_ratio,
        ),
        inflow_outflow_ratio=calculate_inflow_outflow_ratio(group),

        unique_senders=calculate_unique_senders(group),
        unique_receivers=calculate_unique_beneficiaries(group),
        unique_counterparties=len(counterparties_in | counterparties_out),
        reciprocal_counterparty_count=len(counterparties_in & counterparties_out),

        distinct_device_count=int(outgoing["device_id"].nunique(dropna=True)),
        distinct_ip_count=int(outgoing["ip_address"].nunique(dropna=True)),
        max_accounts_sharing_a_device=shared_device,
        max_accounts_sharing_an_ip=shared_ip,

        distinct_country_count=int(outgoing["location_country"].nunique(dropna=True)),
        location_change_count=calculate_location_changes(outgoing),

        crypto_transaction_count=int(len(crypto_rows)),
        crypto_total_amount=float(crypto_rows["amount"].dropna().sum()),

        has_sufficient_baseline=baseline.has_sufficient_baseline,
        baseline_average_amount=baseline.baseline_average_amount,
        baseline_transactions_per_day=baseline.baseline_transactions_per_day,
        baseline_unique_beneficiaries=baseline.baseline_unique_beneficiaries,
        current_period_average_amount=baseline.current_period_average_amount,
        current_period_transactions_per_day=baseline.current_period_transactions_per_day,
        current_period_unique_beneficiaries=baseline.current_period_unique_beneficiaries,

        kyc_status=customer_data.kyc_status if customer_data else "unknown",

        graph=graph_metrics,
        detection=detection_signals,
    )


def _avg_gap_seconds(group: pd.DataFrame) -> Optional[float]:
    sorted_ts = group["timestamp"].sort_values()
    if len(sorted_ts) < 2:
        return None
    gaps = sorted_ts.diff().dropna().dt.total_seconds()
    return float(gaps.mean()) if not gaps.empty else None


# ============================================================================
# Public entry points
# ============================================================================

def extract_features(
    account_id: str,
    transactions: Iterable[TransactionInput],
    reference_time: Optional[pd.Timestamp] = None,
    graph_metrics: Optional[GraphMetrics] = None,
    detection_signals: Optional[DetectionSignals] = None,
    customer_data: Optional[CustomerData] = None,
    device_to_accounts: Optional[Dict[str, Set[str]]] = None,
    ip_to_accounts: Optional[Dict[str, Set[str]]] = None,
    thresholds: RiskThresholds = DEFAULT_THRESHOLDS,
) -> RiskFeatures:
    """
    Single-account path. `transactions` should be this account's involved
    transactions (as sender or receiver).

    device_to_accounts/ip_to_accounts are optional here: without them,
    max_accounts_sharing_a_device/ip will read 0 (not computed), because a
    single account's own transaction list has no visibility into what OTHER
    accounts share its devices/IPs. Build these once with
    build_shared_infrastructure_maps() over your full dataset and pass them
    to every single-account call if you need that signal to be real.
    """
    df = _to_dataframe(transactions)
    if df.empty:
        ref = reference_time if reference_time is not None else pd.Timestamp.now(tz="UTC")
        return _compute_features_for_account(
            account_id, df, ref, thresholds, graph_metrics, detection_signals, customer_data, None, None,
        )

    long_df = _to_long_format(df)
    group = long_df[long_df["account_id"] == account_id]
    ref_time = reference_time if reference_time is not None else df["timestamp"].max()

    return _compute_features_for_account(
        account_id, group, ref_time, thresholds,
        graph_metrics, detection_signals, customer_data,
        device_to_accounts, ip_to_accounts,
    )


def extract_features_bulk(
    transactions: Iterable[TransactionInput],
    account_ids: Optional[Iterable[str]] = None,
    graph_metrics_by_account: Optional[Dict[str, GraphMetrics]] = None,
    detection_signals_by_account: Optional[Dict[str, DetectionSignals]] = None,
    customer_data_by_id: Optional[Dict[str, CustomerData]] = None,
    account_to_customer_id: Optional[Dict[str, str]] = None,
    thresholds: RiskThresholds = DEFAULT_THRESHOLDS,
) -> Dict[str, RiskFeatures]:
    """
    Batch path. Builds the DataFrame once, the cross-account device/IP maps
    once, then computes features per account via a single groupby.

    `account_to_customer_id` + `customer_data_by_id` let KYC status resolve
    per account; both optional, degrading to kyc_status="unknown" if absent.
    """
    transactions = list(transactions)  # consumed twice (dataframe + infra maps)
    df = _to_dataframe(transactions)
    if df.empty:
        return {}

    reference_time = df["timestamp"].max()
    long_df = _to_long_format(df)

    if account_ids is not None:
        target = set(account_ids)
        long_df = long_df[long_df["account_id"].isin(target)]
    if long_df.empty:
        return {}

    device_to_accounts, ip_to_accounts = build_shared_infrastructure_maps(transactions)

    results: Dict[str, RiskFeatures] = {}
    for account_id, group in long_df.groupby("account_id"):
        customer_id = account_to_customer_id.get(account_id) if account_to_customer_id else None
        customer = customer_data_by_id.get(customer_id) if (customer_data_by_id and customer_id) else None

        results[account_id] = _compute_features_for_account(
            account_id, group, reference_time, thresholds,
            graph_metrics=(graph_metrics_by_account or {}).get(account_id),
            detection_signals=(detection_signals_by_account or {}).get(account_id),
            customer_data=customer,
            device_to_accounts=device_to_accounts,
            ip_to_accounts=ip_to_accounts,
        )

    return results
