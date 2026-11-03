import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

LOGGER = logging.getLogger(__name__)


def write_json(data: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def write_frame(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.casefold() == ".parquet":
        try:
            frame.to_parquet(path, index=False)
        except ImportError:
            path = path.with_suffix(".csv")
            frame.to_csv(path, index=False, encoding="utf-8")
            LOGGER.warning("PyArrow is unavailable; wrote CSV fallback to %s", path)
    else:
        frame.to_csv(path, index=False, encoding="utf-8")
    return path