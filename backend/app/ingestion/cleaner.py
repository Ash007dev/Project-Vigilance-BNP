"""Separate usable and unusable transaction rows.

What: Removes duplicates, quarantines broken rows, and flags reviewable rows.
How: Applies clear data-quality rules without suppressing suspicious behavior.
Result: Returns clean rows, quarantined rows, and summary counts.
Example: A missing transaction ID is quarantined.
"""

from typing import Dict, Any, Tuple
import polars as pl


class RecordCleaner:
    """Applies strict data quality classification rules without suppressing AML behavioral signals."""

    IP_REGEX = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"

    def process(self, df: pl.DataFrame) -> Tuple[pl.DataFrame, pl.DataFrame, Dict[str, Any]]:
        working_df = df.clone()
        total_input_rows = working_df.height

        # Remove exact duplicate rows.
        deduped_df = working_df.unique(keep="first")
        total_removed = total_input_rows - deduped_df.height
        working_df = deduped_df

        # Quarantine rows that cannot be used safely.
        quarantine_conditions = []
        quarantine_reasons = []

        # A transaction needs an ID.
        if "transaction_id" in working_df.columns:
            cond = (
                pl.col("transaction_id").is_null() 
                | (pl.col("transaction_id").cast(pl.Utf8).str.strip_chars() == "")
            )
            quarantine_conditions.append(cond)
            quarantine_reasons.append(pl.when(cond).then(pl.lit("missing_transaction_id")))

            # Reused transaction IDs may describe conflicting records.
            txn_counts = working_df.group_by("transaction_id").agg(pl.len().alias("_txn_id_count"))
            working_df = working_df.join(txn_counts, on="transaction_id", how="left")
            conflict_cond = (pl.col("_txn_id_count") > 1) & (pl.col("transaction_id").is_not_null())
            quarantine_conditions.append(conflict_cond)
            quarantine_reasons.append(pl.when(conflict_cond).then(pl.lit("conflicting_transaction_id")))

        # A transaction needs a timestamp.
        if "timestamp" in working_df.columns:
            cond = pl.col("timestamp").is_null()
            quarantine_conditions.append(cond)
            quarantine_reasons.append(pl.when(cond).then(pl.lit("invalid_or_missing_timestamp")))

        # An amount must be a positive number.
        if "amount" in working_df.columns:
            amt_float = pl.col("amount").cast(pl.Float64, strict=False)
            cond = amt_float.is_null() | (amt_float <= 0.0)
            quarantine_conditions.append(cond)
            quarantine_reasons.append(pl.when(cond).then(pl.lit("invalid_or_missing_amount")))

        # The crypto flag must be recognizable.
        if "is_crypto" in working_df.columns:
            cond = pl.col("is_crypto").is_null()
            quarantine_conditions.append(cond)
            quarantine_reasons.append(pl.when(cond).then(pl.lit("unrecognized_is_crypto_value")))

        # A row is quarantined when any required rule fails.
        if quarantine_conditions:
            is_quarantined = pl.lit(False)
            for cond in quarantine_conditions:
                is_quarantined = is_quarantined | cond
            quarantine_reason_expr = pl.coalesce(quarantine_reasons)
        else:
            is_quarantined = pl.lit(False)
            quarantine_reason_expr = pl.lit("none")

        quarantined_df = (
            working_df.filter(is_quarantined)
            .with_columns(quarantine_reason_expr.alias("quarantine_reason"))
            .drop(["_txn_id_count"], strict=False)
        )

        clean_working_df = working_df.filter(~is_quarantined).drop(["_txn_id_count"], strict=False)

        # Keep usable rows and attach review flags.
        flag_exprs = []

        if "is_crypto" in clean_working_df.columns and "crypto_wallet" in clean_working_df.columns:
            wallet_clean = pl.col("crypto_wallet").cast(pl.Utf8).str.strip_chars()
            has_wallet = (
                pl.col("crypto_wallet").is_not_null() 
                & (wallet_clean != "") 
                & (wallet_clean.str.to_lowercase() != "null")
            )
            
            c_missing = (pl.col("is_crypto") == True) & (~has_wallet)
            c_present = (pl.col("is_crypto") == False) & has_wallet
            
            flag_exprs.append(pl.when(c_missing).then(pl.lit("crypto_true_missing_wallet")))
            flag_exprs.append(pl.when(c_present).then(pl.lit("crypto_false_wallet_present")))

        if "ip_address" in clean_working_df.columns:
            ip_str = pl.col("ip_address").cast(pl.Utf8).str.strip_chars()
            invalid_ip_cond = (
                pl.col("ip_address").is_not_null() & 
                (ip_str != "") & 
                (~ip_str.str.contains(self.IP_REGEX))
            )
            flag_exprs.append(pl.when(invalid_ip_cond).then(pl.lit("invalid_ip")))

        if "device_id" in clean_working_df.columns:
            flag_exprs.append(pl.when(pl.col("device_id").is_null() | (pl.col("device_id").cast(pl.Utf8).str.strip_chars() == "")).then(pl.lit("missing_device_id")))

        if "sender_name" in clean_working_df.columns or "sender_customer_id" in clean_working_df.columns:
            s_name_null = pl.col("sender_name").is_null() if "sender_name" in clean_working_df.columns else pl.lit(True)
            s_cid_null = pl.col("sender_customer_id").is_null() if "sender_customer_id" in clean_working_df.columns else pl.lit(True)
            flag_exprs.append(pl.when(s_name_null & s_cid_null).then(pl.lit("incomplete_sender_info")))

        if "receiver_name" in clean_working_df.columns or "receiver_customer_id" in clean_working_df.columns:
            r_name_null = pl.col("receiver_name").is_null() if "receiver_name" in clean_working_df.columns else pl.lit(True)
            r_cid_null = pl.col("receiver_customer_id").is_null() if "receiver_customer_id" in clean_working_df.columns else pl.lit(True)
            flag_exprs.append(pl.when(r_name_null & r_cid_null).then(pl.lit("incomplete_receiver_info")))

        if "sender_account" in clean_working_df.columns and "receiver_account" in clean_working_df.columns:
            self_tx = pl.col("sender_account") == pl.col("receiver_account")
            flag_exprs.append(pl.when(self_tx).then(pl.lit("same_sender_and_receiver")))

        if "amount" in clean_working_df.columns:
            large_tx = pl.col("amount").cast(pl.Float64, strict=False) >= 1000000.0
            flag_exprs.append(pl.when(large_tx).then(pl.lit("large_transaction")))

        if flag_exprs:
            clean_df = clean_working_df.with_columns(
                pl.concat_list(flag_exprs).list.drop_nulls().alias("dq_flags_list")
            ).with_columns(
                pl.when(pl.col("dq_flags_list").list.len() > 0)
                .then(pl.lit("KEEP+FLAG"))
                .otherwise(pl.lit("KEEP"))
                .alias("data_quality_status")
            )
        else:
            clean_df = clean_working_df.with_columns(
                pl.lit([]).cast(pl.List(pl.Utf8)).alias("dq_flags_list"),
                pl.lit("KEEP").alias("data_quality_status")
            )

        # Summarize why rows were quarantined or flagged.
        quarantine_reasons_breakdown = {}
        if quarantined_df.height > 0:
            q_counts = quarantined_df.group_by("quarantine_reason").agg(pl.len().alias("count"))
            for row in q_counts.iter_rows():
                quarantine_reasons_breakdown[row[0]] = row[1]

        flag_reasons_breakdown = {}
        if clean_df.height > 0:
            exploded_flags = clean_df.filter(pl.col("dq_flags_list").list.len() > 0).explode("dq_flags_list")
            if exploded_flags.height > 0:
                f_counts = exploded_flags.group_by("dq_flags_list").agg(pl.len().alias("count"))
                for row in f_counts.iter_rows():
                    flag_reasons_breakdown[row[0]] = row[1]

        # Join flags so the result can be written to CSV.
        clean_df = clean_df.with_columns(
            pl.col("dq_flags_list").list.join("; ").alias("dq_flags")
        ).drop("dq_flags_list")

        stats = {
            "total_input_rows": total_input_rows,
            "clean_usable_records": clean_df.height,
            "keep_clean_rows": clean_df.filter(pl.col("data_quality_status") == "KEEP").height,
            "keep_and_flag_rows": clean_df.filter(pl.col("data_quality_status") == "KEEP+FLAG").height,
            "quarantined_records": quarantined_df.height,
            "removed_duplicate_copies": total_removed,
            "quarantine_reason_breakdown": quarantine_reasons_breakdown,
            "flag_reason_breakdown": flag_reasons_breakdown,
            "integrity_check": (
                total_input_rows == (clean_df.height + quarantined_df.height + total_removed)
            )
        }

        return clean_df, quarantined_df, stats
