"""
Name: workbook.py
Author: Owen Sharpe
Description: parse Bloomberg BDH output laid out as side-by-side Date/Value blocks. Every pull sheet has the same shape: a few title rows, up to three rows of labels (field ID, description, tenor...), a header row of alternating "Date" / "Value" cells, then one block per series. Each block carries its own date column because different series start and skip on different days, so blocks are parsed independently and aligned later in pandas. A failed pull shows up as a Bloomberg error string ("#N/A N/A", "#N/A Invalid Security") in place of a date or value. Those cells are dropped, which leaves a failed block as an empty series rather than an exception.
"""

from __future__ import annotations

# import libraries
import datetime as dt
import warnings
from dataclasses import dataclass
from pathlib import Path

import openpyxl
import pandas as pd

# global variables
_HEADER_SEARCH_ROWS = 15  # how far down to look for the Date/Value header
_MAX_LABEL_ROWS = 3  # how many label rows above it to read.


@dataclass(frozen=True)
class Block:
    sheet: str
    labels: tuple[str, ...]
    series: pd.Series


def _clean(cell: object) -> str | None:
    if cell is None:
        return None
    
    text = str(cell).strip()
    return text or None


def _is_number(cell: object) -> bool:
    return isinstance(cell, (int, float)) and not isinstance(cell, bool)


def _parse_sheet(name: str, rows: list[tuple]) -> list[Block]:
    header = next(
        (
            i
            for i, row in enumerate(rows[:_HEADER_SEARCH_ROWS])
            if any(
                _clean(a) == "Date" and _clean(b) == "Value"
                for a, b in zip(row, row[1:])
            )
        ),
        None,
    )
    
    if header is None:
        return []  # notes sheet, not a pull

    blocks = []
    header_row = rows[header]
    
    for col in range(len(header_row) - 1):
        if not (_clean(header_row[col]) == "Date" and _clean(header_row[col + 1]) == "Value"):
            continue

        # walk upward collecting labels, stopping at a blank row so a title
        # line above the label rows is never mistaken for a label
        labels: list[str] = []
        
        for i in range(header - 1, max(-1, header - 1 - _MAX_LABEL_ROWS), -1):
            
            if not any(_clean(c) for c in rows[i]):
                break
            
            label = _clean(rows[i][col]) if col < len(rows[i]) else None
            
            if label:
                labels.insert(0, label)

        dates, values = [], []
        
        for row in rows[header + 1 :]:
            
            if col + 1 >= len(row):
                continue
            
            date, value = row[col], row[col + 1]
            
            if isinstance(date, dt.datetime) and _is_number(value):
                dates.append(date)
                values.append(float(value))

        series = pd.Series(values, index=pd.DatetimeIndex(dates).normalize(), dtype=float)
        series.index.name = "date"
        
        if series.index.has_duplicates:
            n = int(series.index.duplicated().sum())
            warnings.warn(f"{name} {labels}: dropped {n} duplicate dates, kept the last")
            series = series[~series.index.duplicated(keep="last")]
        
        blocks.append(Block(name, tuple(labels), series.sort_index()))
    return blocks


# Every Date/Value block in every sheet of the workbook at `path`
def read_workbook(path: str | Path) -> list[Block]:
    
    # data_only reads the cached values, so this works on a saved pull without the Bloomberg add-in.
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    
    try:
        return [
            block
            for ws in wb.worksheets
            for block in _parse_sheet(ws.title, list(ws.iter_rows(values_only=True)))
        ]
    finally:
        wb.close()
