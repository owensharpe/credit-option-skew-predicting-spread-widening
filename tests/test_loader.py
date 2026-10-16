"""
Name: test_loader.py
Author: Owen Sharpe
Description: loader tests against a synthetic workbook laid out like a Bloomberg pull. No real data here: the fixture is built in a temp dir, so the tests run in CI
and on any clone without the Bloomberg files.
"""

# import libraries
import datetime as dt

import openpyxl
import pandas as pd
import pytest

# import from our credit engine
from credit_engine.data import CATALOG, SeriesSpec, load_panel, load_series
from credit_engine.data.workbook import read_workbook

D = dt.datetime


@pytest.fixture
def data_dir(tmp_path):
    wb = openpyxl.Workbook()
    notes = wb.active
    notes.title = "Instructions"
    notes["A1"] = "Notes only, no Date/Value header"

    # creating synthetic data
    ws = wb.create_sheet("HYG")
    ws.append(["HYG - title"])
    ws.append(["Ticker: HYG US Equity"])
    ws.append([])
    ws.append(["VL137", None, None, "VL140", None, None, "VL186", None])
    ws.append(["30D IVOL @ 100% mny", None, None, "30D IVOL @ 90% mny", None, None,
               "24M IVOL @ 100% mny", None])
    ws.append(["Date", "Value", None, "Date", "Value", None, "Date", "Value"])

    # different start dates per block, an error value mid-series, a
    # duplicate date, and a block whose pull failed outright
    ws.append([D(2020, 1, 2), 7.5, None, D(2020, 1, 3), 8.4, None, "#N/A N/A", None])
    ws.append([D(2020, 1, 3), 7.6, None, D(2020, 1, 6), "#N/A N/A", None, None, None])
    ws.append([D(2020, 1, 6), 7.7, None, D(2020, 1, 7), 8.6, None, None, None])
    ws.append([D(2020, 1, 6), 7.8, None, None, None, None, None, None])

    wb.save(tmp_path / "pull.xlsx")
    return tmp_path

# pull a specific hit
def spec(name, labels):
    return SeriesSpec(name, "pull.xlsx", "HYG", labels, "HYG US Equity", labels[0], "vol %")


ATM = spec("hyg.atm", ("VL137", "30D IVOL @ 100% mny"))
PUT = spec("hyg.put", ("VL140", "30D IVOL @ 90% mny"))
FAILED = spec("hyg.long", ("VL186", "24M IVOL @ 100% mny"))


def test_reads_blocks_and_skips_notes_sheets(data_dir):
    with pytest.warns(UserWarning, match="duplicate"):
        blocks = read_workbook(data_dir / "pull.xlsx")

    assert {b.sheet for b in blocks} == {"HYG"}
    assert [b.labels for b in blocks] == [ATM.labels, PUT.labels, FAILED.labels]


def test_drops_error_cells_and_keeps_last_duplicate(data_dir):
    with pytest.warns(UserWarning):
        atm = load_series("hyg.atm", data_dir=data_dir, catalog={"hyg.atm": ATM})
        put = load_series("hyg.put", data_dir=data_dir, catalog={"hyg.put": PUT})

    assert atm.to_dict() == {
        pd.Timestamp("2020-01-02"): 7.5,
        pd.Timestamp("2020-01-03"): 7.6,
        pd.Timestamp("2020-01-06"): 7.8,
    }
    assert list(put.index) == [pd.Timestamp("2020-01-03"), pd.Timestamp("2020-01-07")]


def test_panel_aligns_on_union_without_filling(data_dir):
    with pytest.warns(UserWarning):
        panel = load_panel(data_dir=data_dir, catalog={"hyg.atm": ATM, "hyg.put": PUT})
        
    assert list(panel.columns) == ["hyg.atm", "hyg.put"]
    assert len(panel) == 4
    assert pd.isna(panel.loc["2020-01-02", "hyg.put"])
    assert pd.isna(panel.loc["2020-01-07", "hyg.atm"])


def test_failed_pull_is_an_error(data_dir):
    with pytest.warns(UserWarning), pytest.raises(ValueError, match="no data"):
        load_panel(data_dir=data_dir, catalog={"hyg.long": FAILED})


def test_renamed_label_is_an_error(data_dir):
    renamed = spec("hyg.atm", ("VL137", "30D IVOL @ 100%"))
    with pytest.warns(UserWarning), pytest.raises(KeyError, match="Labels on that sheet"):
        load_panel(data_dir=data_dir, catalog={"hyg.atm": renamed})


def test_missing_workbook_points_at_readme(tmp_path):
    with pytest.raises(FileNotFoundError, match="README"):
        load_panel(data_dir=tmp_path, catalog={"hyg.atm": ATM})


def test_catalog_entries_are_unique_and_well_formed():
    keys = [(s.workbook, s.sheet, s.labels) for s in CATALOG.values()]
    assert len(keys) == len(set(keys))
    for name, s in CATALOG.items():
        assert name == s.name
        assert s.ticker and s.field and s.units
