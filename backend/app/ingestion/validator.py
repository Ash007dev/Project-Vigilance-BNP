"""Report transaction data problems.

What: Checks required fields, amounts, IP addresses, and crypto values.
How: Counts each type of issue without changing source values.
Result: Returns the DataFrame and a validation report.
Example: A negative amount is reported as ``INVALID_OR_NEGATIVE_AMOUNT``.
"""

from typing import Dict, Any, Tuple, List
import polars as pl

class DataValidator:
    """Validates structural and domain rules without modifying data."""

    # Accept only complete IPv4 addresses.
    IP_REGEX = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"

    def validate(self, df: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        validated_df = df.with_columns(
            pl.lit([]).cast(pl.List(pl.Utf8)).alias("_validation_issues")
        )

        # Report missing transaction fields.
        for req_col in ["transaction_id", "timestamp", "sender_account", "receiver_account", "amount"]:
            if req_col not in validated_df.columns:
                issues.append({
                    "issue_type": "MISSING_REQUIRED_COLUMN",
                    "affected_column": req_col,
                    "affected_rows": df.height,
                    "severity": "CRITICAL"
                })

        # Report missing transaction IDs.
        if "transaction_id" in validated_df.columns:
            null_txn = validated_df.filter(
                pl.col("transaction_id").is_null() | 
                (pl.col("transaction_id").cast(pl.Utf8).str.strip_chars() == "")
            )
            if null_txn.height > 0:
                issues.append({
                    "issue_type": "INVALID_TRANSACTION_ID",
                    "affected_column": "transaction_id",
                    "affected_rows": null_txn.height,
                    "severity": "CRITICAL"
                })

        # Report missing or non-positive amounts.
        if "amount" in validated_df.columns:
            invalid_amt = validated_df.filter(
                pl.col("amount").is_null() | (pl.col("amount") <= 0)
            )
            if invalid_amt.height > 0:
                issues.append({
                    "issue_type": "INVALID_OR_NEGATIVE_AMOUNT",
                    "affected_column": "amount",
                    "affected_rows": invalid_amt.height,
                    "severity": "HIGH"
                })

        # Report invalid IP addresses without rejecting the row.
        if "ip_address" in validated_df.columns:
            invalid_ip = validated_df.filter(
                pl.col("ip_address").is_not_null() &
                (pl.col("ip_address").cast(pl.Utf8).str.strip_chars() != "") &
                (~pl.col("ip_address").cast(pl.Utf8).str.strip_chars().str.contains(self.IP_REGEX))
            )
            if invalid_ip.height > 0:
                issues.append({
                    "issue_type": "INVALID_IP_FORMAT",
                    "affected_column": "ip_address",
                    "affected_rows": invalid_ip.height,
                    "severity": "MEDIUM"
                })

        # Report crypto flags that disagree with wallet data.
        if "is_crypto" in validated_df.columns and "crypto_wallet" in validated_df.columns:
            wallet_clean = pl.col("crypto_wallet").cast(pl.Utf8).str.strip_chars()
            has_wallet = pl.col("crypto_wallet").is_not_null() & (wallet_clean != "") & (wallet_clean.str.to_lowercase() != "null")
            
            crypto_no_wallet = validated_df.filter((pl.col("is_crypto") == True) & (~has_wallet))
            non_crypto_wallet = validated_df.filter((pl.col("is_crypto") == False) & has_wallet)

            if crypto_no_wallet.height > 0:
                issues.append({"issue_type": "CRYPTO_TRUE_MISSING_WALLET", "affected_rows": crypto_no_wallet.height})
            if non_crypto_wallet.height > 0:
                issues.append({"issue_type": "CRYPTO_FALSE_WALLET_PRESENT", "affected_rows": non_crypto_wallet.height})

        validation_report = {"total_issues_found": len(issues), "issues": issues}
        return validated_df, validation_report
