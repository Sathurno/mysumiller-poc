import pandas as pd

from .cleaning import parse_vintage_list


def add_catalog_features(wines: pd.DataFrame) -> pd.DataFrame:
    featured = wines.copy(deep=True)
    if "Grapes" in featured:
        featured["GrapeCount"] = featured["Grapes"].map(
            lambda value: len(value) if isinstance(value, list) else pd.NA
        ).astype("Int64")
    if "Vintages" in featured:
        normalized = featured["Vintages"].map(parse_vintage_list)
        featured["VintageCount"] = normalized.map(
            lambda value: sum(isinstance(item, int) for item in value) if value is not None else pd.NA
        ).astype("Int64")
        featured["HasNonVintage"] = normalized.map(
            lambda value: "N.V." in value if value is not None else pd.NA
        ).astype("boolean")
    return featured