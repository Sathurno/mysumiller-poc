from collections.abc import Iterable

import pandas as pd

from .config import RATING_COLUMNS, WINE_COLUMNS


def clean_ratings(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    cleaned = frame.copy(deep=True)
    for column in ("RatingID", "UserID", "WineID"):
        if column in cleaned:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").astype("Int64")
    if "Vintage" in cleaned:
        cleaned["Vintage"] = pd.to_numeric(cleaned["Vintage"], errors="coerce").astype("Int64")
    if "Rating" in cleaned:
        cleaned["Rating"] = pd.to_numeric(cleaned["Rating"], errors="coerce")
    invalid_dates = 0
    if "Date" in cleaned:
        parsed = pd.to_datetime(cleaned["Date"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
        invalid_dates = int((cleaned["Date"].notna() & parsed.isna()).sum())
        cleaned["Date"] = parsed
    cleaned["source"] = "X-Wines"
    return cleaned, {"invalid_dates": invalid_dates}


def validate_schema(frame: pd.DataFrame, dataset: str) -> dict[str, object]:
    expected = WINE_COLUMNS if dataset == "wines" else RATING_COLUMNS
    missing = [column for column in expected if column not in frame.columns]
    unexpected = [column for column in frame.columns if column not in expected]
    return {
        "dataset": dataset,
        "valid": not missing,
        "missing_columns": missing,
        "unexpected_columns": unexpected,
    }


def validate_ratings(
    ratings: pd.DataFrame,
    wine_ids: Iterable[object] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "row_count": int(len(ratings)),
        "missing_ids": {
            column: int(ratings[column].isna().sum())
            for column in ("RatingID", "UserID", "WineID")
            if column in ratings
        },
        "duplicate_rating_ids": int(ratings["RatingID"].duplicated(keep=False).sum())
        if "RatingID" in ratings else None,
        "exact_duplicate_rows": int(ratings.duplicated().sum()),
    }
    if "Rating" in ratings:
        numeric = pd.to_numeric(ratings["Rating"], errors="coerce")
        result["invalid_rating_count"] = int((numeric.notna() & ~numeric.between(1, 5)).sum())
        result["missing_or_unparseable_rating_count"] = int(numeric.isna().sum())
        result["rating_values"] = sorted(float(value) for value in numeric.dropna().unique())
        in_range = numeric.between(1, 5)
        compatible = numeric.mod(0.5).abs().le(1e-8)
        result["half_star_compatible_count"] = int((in_range & compatible).sum())
        result["incompatible_half_star_count"] = int((in_range & ~compatible).sum())
    repeated_key = [column for column in ("UserID", "WineID", "Vintage", "Date") if column in ratings]
    result["repeated_user_wine_vintage_time_rows"] = (
        int(ratings.duplicated(subset=repeated_key, keep=False).sum()) if len(repeated_key) > 1 else 0
    )
    if wine_ids is not None and "WineID" in ratings:
        available = set(wine_ids)
        valid_wine_ids = ratings["WineID"].dropna()
        unmatched = ~valid_wine_ids.isin(available)
        result["unmatched_wine_id_count"] = int(unmatched.sum())
        result["matched_wine_id_count"] = int((~unmatched).sum())
        result["wine_id_match_rate"] = float((~unmatched).mean()) if len(valid_wine_ids) else None
    return result