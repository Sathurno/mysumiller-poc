import hashlib
import csv
import json
from pathlib import Path
from typing import Iterator

import pandas as pd


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_csv(path: Path, encoding: str = "utf-8-sig") -> dict[str, object]:
    with path.open("rb") as file:
        prefix = file.read(4)
        file.seek(0)
        sample = file.read(64 * 1024).decode(encoding, errors="strict")
    bom = "utf-8" if prefix.startswith(b"\xef\xbb\xbf") else None
    delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    header = pd.read_csv(path, encoding=encoding, nrows=0)
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "encoding": encoding,
        "bom": bom,
        "delimiter": delimiter,
        "columns": header.columns.tolist(),
    }


def read_wines(path: Path, encoding: str = "utf-8-sig") -> pd.DataFrame:
    return pd.read_csv(path, encoding=encoding, low_memory=False)


def iter_ratings(
    path: Path,
    chunksize: int = 500_000,
    encoding: str = "utf-8-sig",
) -> Iterator[pd.DataFrame]:
    yield from pd.read_csv(path, encoding=encoding, chunksize=chunksize, low_memory=False)


def sample_ratings(
    path: Path,
    sample_size: int = 100_000,
    seed: int = 42,
    chunksize: int = 500_000,
    encoding: str = "utf-8-sig",
) -> tuple[pd.DataFrame, dict[str, object]]:
    import numpy as np

    if sample_size < 1:
        raise ValueError("sample_size must be positive")
    random = np.random.default_rng(seed)
    selected = pd.DataFrame()
    rows_scanned = 0
    for chunk in iter_ratings(path, chunksize=chunksize, encoding=encoding):
        chunk_size = len(chunk)
        rows_scanned += chunk_size
        chunk["_sample_key"] = random.random(chunk_size)
        selected = pd.concat([selected, chunk], ignore_index=True)
        if len(selected) > sample_size:
            selected = selected.nsmallest(sample_size, "_sample_key").reset_index(drop=True)
    selected = selected.nsmallest(sample_size, "_sample_key").drop(columns="_sample_key")
    selected = selected.sort_values("RatingID", kind="stable").reset_index(drop=True)
    return selected, {
        "sampling_method": "uniform_priority_sample_without_replacement",
        "seed": seed,
        "sample_size": int(len(selected)),
        "requested_sample_size": sample_size,
        "source_rows_scanned": rows_scanned,
        "is_random_sample": True,
    }


def load_or_create_ratings_sample(
    source_path: Path,
    sample_path: Path,
    metadata_path: Path,
    sample_size: int = 100_000,
    seed: int = 42,
) -> tuple[pd.DataFrame, dict[str, object]]:
    source_stat = source_path.stat()
    source_identity = {"size_bytes": source_stat.st_size, "mtime_ns": source_stat.st_mtime_ns}
    if sample_path.exists() and metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (metadata.get("source_identity") == source_identity
                and metadata.get("sample_size") == sample_size
                and metadata.get("seed") == seed):
            return pd.read_csv(sample_path, low_memory=False), metadata["sampling"]

    sample, sampling = sample_ratings(source_path, sample_size=sample_size, seed=seed)
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(sample_path, index=False, encoding="utf-8")
    metadata = {
        "source_identity": source_identity,
        "sample_size": sample_size,
        "seed": seed,
        "sampling": sampling,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return sample, sampling