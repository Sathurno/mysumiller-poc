import ast
import re
from collections.abc import Iterable

import pandas as pd

NULL_TOKENS = {"", "na", "n/a", "null", "<na>"}
STRING_COLUMNS = [
    "WineName", "Type", "Elaborate", "Body", "Acidity", "Code", "Country",
    "RegionName", "WineryName", "Website",
]
LIST_COLUMNS = ["Grapes", "Harmonize", "Vintages"]
INTEGER_COLUMNS = ["WineID", "RegionID", "WineryID"]


def normalize_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    cleaned = re.sub(r"\s+", " ", value).strip()
    return pd.NA if cleaned.casefold() in NULL_TOKENS else cleaned


def parse_list_value(value: object) -> tuple[list[object] | None, str | None]:
    if value is None or value is pd.NA:
        return None, None
    if isinstance(value, float) and pd.isna(value):
        return None, None
    if isinstance(value, list):
        return value, None
    if not isinstance(value, str):
        return None, f"expected list text, got {type(value).__name__}"
    text = value.strip()
    if not text:
        return None, None
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError) as error:
        return None, f"invalid list literal: {error.__class__.__name__}"
    if not isinstance(parsed, list):
        return None, f"expected list, got {type(parsed).__name__}"
    return parsed, None


def clean_wines(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cleaned = frame.copy(deep=True)
    for column in STRING_COLUMNS:
        if column in cleaned:
            cleaned[column] = cleaned[column].map(normalize_text)
    for column in INTEGER_COLUMNS:
        if column in cleaned:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").astype("Int64")
    if "ABV" in cleaned:
        cleaned["ABV"] = pd.to_numeric(cleaned["ABV"], errors="coerce")

    errors: list[dict[str, object]] = []
    for column in LIST_COLUMNS:
        if column not in cleaned:
            continue
        parsed_values = []
        for index, value in cleaned[column].items():
            parsed, error = parse_list_value(value)
            parsed_values.append(parsed)
            if error:
                errors.append({"row_index": index, "column": column, "value": value, "error": error})
        cleaned[column] = parsed_values
    return cleaned, pd.DataFrame(errors, columns=["row_index", "column", "value", "error"])


def parse_vintage_list(values: Iterable[object] | None) -> list[int | str] | None:
    if values is None:
        return None
    result: list[int | str] = []
    for value in values:
        if isinstance(value, int) and not isinstance(value, bool):
            result.append(value)
        elif isinstance(value, str) and value.strip().casefold() == "n.v.":
            result.append("N.V.")
        else:
            try:
                result.append(int(str(value).strip()))
            except (TypeError, ValueError):
                continue
    return result