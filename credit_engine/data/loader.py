"""
Name: loader.py
Author: Owen Sharpe
Description: load catalog series from the local Bloomberg pulls. Parsing the workbooks takes a while, so the first load writes every catalog series to data/processed/series.parquet and later loads read that instead. The cache rebuilds itself whenever a source workbook is newer than it.
"""

from __future__ import annotations

# import libraries
import os
from collections.abc import Iterable, Mapping
from pathlib import Path

import pandas as pd

# import from our scripts
from credit_engine.data.catalog import CATALOG, SeriesSpec
from credit_engine.data.workbook import read_workbook

# global variables
DEFAULT_DATA_DIR = Path(
    os.environ.get("CREDIT_ENGINE_DATA", Path(__file__).resolve().parents[2] / "data")
)
CACHE_NAME = "processed/series.parquet"


# using frame (name, date, value) for every series in `catalog`.
def _parse(catalog: Mapping[str, SeriesSpec], data_dir: Path) -> pd.DataFrame:
    frames = []
    
    for workbook in sorted({spec.workbook for spec in catalog.values()}):
        path = data_dir / workbook
        
        if not path.exists():
            raise FileNotFoundError(
                f"{path} is missing. The Bloomberg pulls aren't in the repo; "
                "see the README for how to rebuild them."
            )
        
        blocks = {(b.sheet, b.labels): b.series for b in read_workbook(path)}

        for spec in (s for s in catalog.values() if s.workbook == workbook):
            
            series = blocks.get((spec.sheet, spec.labels))
            
            if series is None:
                available = [labels for sheet, labels in blocks if sheet == spec.sheet]
                
                raise KeyError(
                    f"{spec.name}: no block labelled {spec.labels} on sheet "
                    f"{spec.sheet!r} of {workbook}. Labels on that sheet: {available}"
                )
            
            if series.empty:
                raise ValueError(f"{spec.name}: block {spec.labels} has no data")
            
            frames.append(
                series.rename("value").reset_index().assign(name=spec.name)
            )
    return pd.concat(frames, ignore_index=True)[["name", "date", "value"]]


def _load_all(data_dir: Path, cache: bool) -> pd.DataFrame:
    cache_path = data_dir / CACHE_NAME
    sources = [data_dir / w for w in {s.workbook for s in CATALOG.values()}]
    
    if (
        cache
        and cache_path.exists()
        and all(p.exists() for p in sources)
        and cache_path.stat().st_mtime >= max(p.stat().st_mtime for p in sources)
    ):
        frame = pd.read_parquet(cache_path)
        if set(frame["name"].unique()) == set(CATALOG):
            return frame

    frame = _parse(CATALOG, data_dir)
    
    if cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(cache_path, index=False)
    return frame


# wide frame, one column per series, on the union of their dates
# a NaN means Bloomberg had no print that day, and deciding what to do about it belongs to the analysis
#  Passing `catalog` parses just those specs and skips the cache, which is what the tests use
def load_panel(
    names: Iterable[str] | None = None,
    *,
    data_dir: str | Path | None = None,
    catalog: Mapping[str, SeriesSpec] | None = None,
    cache: bool = True,
) -> pd.DataFrame:

    data_dir = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    
    if catalog is None:
        frame = _load_all(data_dir, cache)
        known = CATALOG
    else:
        frame = _parse(catalog, data_dir)
        known = catalog

    names = list(names) if names is not None else list(known)
    unknown = [n for n in names if n not in known]
    
    if unknown:
        raise KeyError(f"not in the catalog: {unknown}")

    wide = (
        frame[frame["name"].isin(names)]
        .pivot(index="date", columns="name", values="value")
        .sort_index()
    )
    wide.columns.name = None
    return wide[names]


# one series with only the dates it has 
def load_series(name: str, **kwargs) -> pd.Series:
    return load_panel([name], **kwargs)[name].dropna()


# parse every workbook and write the parquet cache
def build_cache(data_dir: str | Path | None = None) -> Path:
    data_dir = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    
    _load_all(data_dir, cache=False).to_parquet(
        _ensure_parent(data_dir / CACHE_NAME), index=False
    )
    return data_dir / CACHE_NAME


def _ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


if __name__ == "__main__":
    path = build_cache()
    frame = pd.read_parquet(path)
    summary = frame.groupby("name")["date"].agg(["min", "max", "count"])
    
    with pd.option_context("display.max_rows", None, "display.width", 120):
        print(summary)
    print(f"\n{len(summary)} series cached to {path}")
