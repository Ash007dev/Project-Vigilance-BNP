"""Map source columns to the transaction schema.

What: Recognizes common names such as ``Txn ID`` and ``From Account``.
How: Compares simple normalized names with a list of known aliases.
Result: Returns canonical columns and a mapping report.
Example: ``Txn ID`` becomes ``transaction_id``.
"""

import re
from typing import Dict, List, Tuple, Any
import polars as pl

CANONICAL_SCHEMA: Dict[str, str] = {
    "transaction_id": "Required",
    "timestamp": "Required",
    "sender_account": "Required",
    "sender_name": "Optional",
    "sender_customer_id": "Optional",
    "receiver_account": "Required",
    "receiver_name": "Optional",
    "receiver_customer_id": "Optional",
    "amount": "Required",
    "currency": "Optional",
    "channel": "Optional",
    "ip_address": "Optional",
    "device_id": "Optional",
    "location_country": "Optional",
    "location_city": "Optional",
    "is_crypto": "Optional",
    "crypto_wallet": "Optional",
}

DEFAULT_ALIASES: Dict[str, List[str]] = {
    "transaction_id": ["txnid", "tx_id", "transactionid", "trans_id", "reference_no", "txn_ref"],
    "timestamp": ["date", "time", "txn_date", "created_at", "trans_time", "datetime"],
    "sender_account": ["fromaccount", "src_acc", "sender_acc", "source_account", "from_acc", "remitter_account"],
    "sender_name": ["sender", "from_name", "remitter_name", "src_name"],
    "sender_customer_id": ["sender_cid", "src_cust_id", "from_customer_id"],
    "receiver_account": ["toaccount", "dst_acc", "receiver_acc", "target_account", "to_acc", "beneficiary_account"],
    "receiver_name": ["receiver", "to_name", "beneficiary_name", "dst_name"],
    "receiver_customer_id": ["receiver_cid", "dst_cust_id", "to_customer_id"],
    "amount": ["value", "txn_amount", "amt", "volume", "sum", "trans_amount"],
    "currency": ["curr", "ccy", "currency_code"],
    "channel": ["paymentmethod", "payment_mode", "txn_type", "channel_type", "type"],
    "ip_address": ["ip", "client_ip", "sender_ip", "ipaddress"],
    "device_id": ["device", "mac_address", "hardware_id", "device_fingerprint"],
    "location_country": ["country", "sender_country", "dest_country", "geo_country"],
    "location_city": ["city", "sender_city", "dest_city", "geo_city"],
    "is_crypto": ["crypto_flag", "is_virtual_asset", "crypto"],
    "crypto_wallet": ["wallet_address", "crypto_address", "wallet", "public_key"],
}


class ColumnMapper:
    """Maps dynamic CSV/XLSX columns to the canonical AML schema."""

    def __init__(self, aliases: Dict[str, List[str]] | None = None) -> None:
        self.aliases = aliases if aliases is not None else DEFAULT_ALIASES

    def _normalize_name(self, col_name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", col_name.lower().strip())

    def map_schema(self, df: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, Any]]:
        """Maps DataFrame headers and generates a mapping report."""
        original_cols = df.columns
        normalized_orig = {col: self._normalize_name(col) for col in original_cols}
        
        mapping: Dict[str, str] = {}
        ambiguous_mappings: Dict[str, List[str]] = {}
        for canonical_col, alias_list in self.aliases.items():
            candidates = []
            target_set = {self._normalize_name(canonical_col)} | {self._normalize_name(a) for a in alias_list}
            
            for orig_col, norm_orig in normalized_orig.items():
                if norm_orig in target_set:
                    candidates.append(orig_col)

            if len(candidates) == 1:
                mapping[candidates[0]] = canonical_col
            elif len(candidates) > 1:
                ambiguous_mappings[canonical_col] = candidates

        # Keep unknown columns unchanged so no source data is lost.
        rename_dict = {}
        unmapped_original = []
        for col in original_cols:
            if col in mapping:
                rename_dict[col] = mapping[col]
            else:
                unmapped_original.append(col)

        mapped_df = df.rename(rename_dict)

        # Report which required and optional fields are available.
        missing_required = []
        missing_optional = []
        for col, req_type in CANONICAL_SCHEMA.items():
            if col not in mapped_df.columns:
                if req_type == "Required":
                    missing_required.append(col)
                else:
                    missing_optional.append(col)

        # Count null values separately from missing columns.
        null_counts = {}
        for col in mapped_df.columns:
            null_counts[col] = mapped_df[col].null_count()

        mapping_report = {
            "mapped_columns": mapping,
            "unmapped_original_columns": unmapped_original,
            "ambiguous_mappings": ambiguous_mappings,
            "missing_required_fields": missing_required,
            "missing_optional_fields": missing_optional,
            "null_value_counts_by_col": null_counts,
            "capabilities_status": {
                "crypto_detection": ("is_crypto" in mapped_df.columns or "crypto_wallet" in mapped_df.columns),
                "geo_tracking": ("location_country" in mapped_df.columns or "ip_address" in mapped_df.columns),
                "device_profiling": "device_id" in mapped_df.columns,
            }
        }

        return mapped_df, mapping_report
