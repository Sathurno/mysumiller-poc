import re
from difflib import SequenceMatcher

import pandas as pd


def _key(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def find_duplicate_candidates(
    wines: pd.DataFrame,
    threshold: float = 0.92,
    max_candidates: int = 10_000,
) -> pd.DataFrame:
    required = {"WineID", "WineName", "Country", "Type"}
    if not required.issubset(wines.columns):
        return pd.DataFrame(columns=["WineID_A", "WineID_B", "name_similarity", "blocking_fields"])

    records = wines.copy()
    records["_name_key"] = records["WineName"].map(_key)
    blocking = [column for column in ("Country", "RegionName", "WineryName", "Type") if column in records]
    records["_block"] = records[blocking].fillna("").astype(str).agg("|".join, axis=1)
    candidates: list[dict[str, object]] = []
    for _, group in records[records["_name_key"].ne("")].groupby("_block", sort=False):
        if len(group) > 200:
            continue
        rows = list(group[["WineID", "_name_key"]].itertuples(index=False, name=None))
        for left_index, (left_id, left_name) in enumerate(rows):
            for right_id, right_name in rows[left_index + 1:]:
                if left_id == right_id:
                    continue
                score = SequenceMatcher(None, left_name, right_name).ratio()
                if score >= threshold:
                    candidates.append({
                        "WineID_A": left_id,
                        "WineID_B": right_id,
                        "name_similarity": round(score, 4),
                        "blocking_fields": ",".join(blocking),
                    })
                    if len(candidates) >= max_candidates:
                        return pd.DataFrame(candidates)
    return pd.DataFrame(
        candidates,
        columns=["WineID_A", "WineID_B", "name_similarity", "blocking_fields"],
    )