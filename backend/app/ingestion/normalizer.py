"""Module for standardizing formats, strings, and types without semantic loss."""

from typing import Tuple, Dict, Any
import polars as pl

class DataNormalizer:
    """Normalizes formatting without modifying underlying business meaning."""

    KNOWN_CURRENCIES = {
        "inr": "INR", "usd": "USD", "eur": "EUR", "gbp": "GBP", 
        "usdt": "USDT", "btc": "BTC", "aud": "AUD", "cad": "CAD"
    }

    KNOWN_CHANNELS = {
        "rtgs": "RTGS", "neft": "NEFT", "upi": "UPI", "swift": "SWIFT", 
        "ach": "ACH", "wire": "WIRE", "netbanking": "NETBANKING", 
        "card": "CARD", "crypto gateway": "Crypto Gateway", "imps": "IMPS"
    }

    def normalize(self, df: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, Any]]:
        norm_df = df.clone()

        # 1. Clean Country & Channel Strings (Trim & Normalize Case)
        if "location_country" in norm_df.columns:
            norm_df = norm_df.with_columns(
                pl.when(pl.col("location_country").is_not_null())
                .then(
                    pl.col("location_country")
                    .cast(pl.Utf8)
                    .str.strip_chars()
                    .str.to_titlecase()
                )
                .otherwise(pl.col("location_country"))
                .alias("location_country")
            )

        if "channel" in norm_df.columns:
            # Match against known channel mapping or default to Titlecase
            norm_df = norm_df.with_columns(
                pl.when(pl.col("channel").is_not_null())
                .then(
                    pl.col("channel")
                    .cast(pl.Utf8)
                    .str.strip_chars()
                    .str.to_lowercase()
                    .replace(self.KNOWN_CHANNELS, default=pl.col("channel").cast(pl.Utf8).str.strip_chars().str.to_titlecase())
                )
                .otherwise(pl.col("channel"))
                .alias("channel")
            )

        if "currency" in norm_df.columns:
            norm_df = norm_df.with_columns(
                pl.when(pl.col("currency").is_not_null())
                .then(
                    pl.col("currency")
                    .cast(pl.Utf8)
                    .str.strip_chars()
                    .str.to_lowercase()
                    .replace(self.KNOWN_CURRENCIES, default=pl.col("currency").cast(pl.Utf8).str.strip_chars().str.to_uppercase())
                )
                .otherwise(pl.col("currency"))
                .alias("currency")
            )

        # 2. Standardize City Titles
        if "location_city" in norm_df.columns:
            norm_df = norm_df.with_columns(
                pl.when(pl.col("location_city").is_not_null())
                .then(pl.col("location_city").cast(pl.Utf8).str.strip_chars().str.to_titlecase())
                .otherwise(pl.col("location_city"))
                .alias("location_city")
            )

        # 3. Parse Amounts safely to Float64 (Preserve signs; remove currency symbols and commas)
        if "amount" in norm_df.columns:
            norm_df = norm_df.with_columns(
                pl.col("amount")
                .cast(pl.Utf8)
                .str.replace_all(r"[\$,]", "")
                .str.strip_chars()
                .cast(pl.Float64, strict=False)
                .alias("amount")
            )

        # 4. Parse Timestamps safely to UTC Datetime using Chrono Fractional Formats
        if "timestamp" in norm_df.columns:
            ts_col = pl.col("timestamp").cast(pl.Utf8).str.strip_chars()
            norm_df = norm_df.with_columns(
                pl.coalesce([
                    ts_col.str.to_datetime("%Y-%m-%dT%H:%M:%S%.3fZ", strict=False),
                    ts_col.str.to_datetime("%Y-%m-%dT%H:%M:%S%.6fZ", strict=False),
                    ts_col.str.to_datetime("%Y-%m-%dT%H:%M:%SZ", strict=False),
                    ts_col.str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
                    ts_col.str.to_datetime("%Y-%m-%d", strict=False),
                    ts_col.str.to_datetime("%d/%m/%Y %H:%M:%S", strict=False),
                ]).alias("timestamp")
            )

        # 5. Normalize Boolean is_crypto Indicator
        if "is_crypto" in norm_df.columns:
            norm_df = norm_df.with_columns(
                pl.when(pl.col("is_crypto").cast(pl.Utf8).str.strip_chars().str.to_lowercase().is_in(["true", "1", "yes", "t"]))
                .then(True)
                .when(pl.col("is_crypto").cast(pl.Utf8).str.strip_chars().str.to_lowercase().is_in(["false", "0", "no", "f"]))
                .then(False)
                .otherwise(None)
                .alias("is_crypto")
            )

        stats = {"normalized_columns": norm_df.columns, "status": "SUCCESS"}
        return norm_df, stats