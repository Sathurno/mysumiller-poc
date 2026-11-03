from collections.abc import Iterable

import pandas as pd


def profile_frame(
    frame: pd.DataFrame,
    identifier_columns: Iterable[str] = (),
    top_categories: int = 20,
) -> dict[str, object]:
    columns: dict[str, object] = {}
    for name in frame.columns:
        series = frame[name]
        item: dict[str, object] = {
            "dtype": str(series.dtype),
            "null_count": int(series.isna().sum()),
            "null_percent": float(series.isna().mean() * 100) if len(series) else 0.0,
            "distinct_count": int(series.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(series):
            non_null = series.dropna()
            item["minimum"] = None if non_null.empty else float(non_null.min())
            item["maximum"] = None if non_null.empty else float(non_null.max())
        else:
            item["top_values"] = {
                str(key)[:120]: int(value)
                for key, value in series.value_counts(dropna=False).head(top_categories).items()
            }
        columns[str(name)] = item

    duplicate_ids = {
        column: int(frame[column].duplicated(keep=False).sum())
        for column in identifier_columns
        if column in frame
    }
    return {
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "columns": columns,
        "exact_duplicate_rows": int(frame.duplicated().sum()),
        "duplicate_identifier_rows": duplicate_ids,
        "memory_bytes": int(frame.memory_usage(index=True, deep=True).sum()),
    }