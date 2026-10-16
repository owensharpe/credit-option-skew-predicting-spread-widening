# Does Credit Option Skew Predict Spread Widening?

I'm building a credit analytics engine and using it to test whether skew in credit ETF options predicts spread widening once you strip out the part of skew that comes mechanically from measuring in price instead of spread.

**Status:** In progress. Right now the repo has the data loader. The pricing engine and the paper's tests come next.

## Data

All the data comes from Bloomberg and isn't included here, because Bloomberg data can't be redistributed. To run anything you need terminal access to re-pull it. The tables below list every ticker and field the code uses.

Tickers marked † follow standard Bloomberg naming but weren't recorded at pull time. Check them in `SECF` before re-pulling.

### Credit ETF options and prices

Tickers: `HYG US Equity`, `LQD US Equity`, `JNK US Equity`. Daily from 1/1/2010.

| Field                | What it is                      |
| -------------------- | ------------------------------- |
| `VL130`              | 1M implied vol, 100% moneyness  |
| `VL137`              | 30D implied vol, 100% moneyness |
| `VL140`              | 30D implied vol, 90% moneyness  |
| `VL134`              | 30D implied vol, 110% moneyness |
| `VL151`              | 60D implied vol, 100% moneyness |
| `VL165`              | 6M implied vol, 100% moneyness  |
| `VL168`              | 6M implied vol, 90% moneyness   |
| `VL162`              | 6M implied vol, 110% moneyness  |
| `VL186`              | 24M implied vol, 100% moneyness |
| `RK903`              | 1M call implied vol, 25 delta   |
| `PX_LAST`            | Close price                     |
| `PX_VOLUME`          | Share volume                    |
| `FUND_NET_ASSET_VAL` | NAV                             |
| `EQY_SH_OUT`         | Shares outstanding              |
| `VOLATILITY_30D`     | 30-day realized vol             |
| `VOLATILITY_90D`     | 90-day realized vol             |

### CDX and iTraxx (`PX_LAST`, daily from 1/1/2005)

| Ticker                               | Quoted as  |
| ------------------------------------ | ---------- |
| `CDX HY CDSI GEN 5Y PRC Corp`        | Price      |
| `CDX HY CDSI GEN 5Y SPRD Corp`       | Spread, bp |
| `CDX IG CDSI GEN 5Y Corp`            | Spread, bp |
| `CDX IG CDSI GEN 3Y Corp` †          | Spread, bp |
| `CDX IG CDSI GEN 7Y Corp`            | Spread, bp |
| `CDX IG CDSI GEN 10Y Corp`           | Spread, bp |
| `CDX HY CDSI GEN 7Y SPRD Corp` †     | Spread, bp |
| `CDX HY CDSI GEN 3Y PRC Corp` †      | Price      |
| `CDX HY CDSI GEN 7Y PRC Corp` †      | Price      |
| `ITRX EUR CDSI GEN 5Y Corp`          | Spread, bp |
| `ITRX EUR CDSI GEN 10Y Corp` †       | Spread, bp |
| `ITRX EUR SNRFIN CDSI GEN 5Y Corp` † | Spread, bp |

HY has both a price and a spread ticker because HY trades on price. IG only has spread. That asymmetry is the point of the paper.

### Equity controls (daily from 1/1/2010)

| Ticker            | Fields                    |
| ----------------- | ------------------------- |
| `SPY US Equity` † | `VL137`, `VL140`, `VL134` |
| `VIX Index` †     | `PX_LAST`                 |
| `SPX Index` †     | `PX_LAST`                 |

### Rates (`PX_LAST`, daily from 1/1/2005)

| Curve           | Tickers                                                                                                                     |
| --------------- | --------------------------------------------------------------------------------------------------------------------------- |
| SOFR OIS (S490) | `USOSFRA`†, `B`†, `C`†, `F`†, `I`† (1M, 2M, 3M, 6M, 9M), `USOSFR1`, `2`†, `3`†, `4`†, `5`, `7`†, `10` (years), all `Curncy` |
| Fed Funds OIS   | `USSOA`†, `C`†, `F`† (1M, 3M, 6M), `USSO1`†, `2`†, `3`†, `5`, `7`†, `10`† (years), all `Curncy`                             |
| Treasuries      | `USGG3M`†, `USGG2YR`†, `USGG5YR`, `USGG10YR`†, `USGG30YR`† `Index`; `USYC2Y10 Index`† for 2s10s                             |

SOFR OIS history before 2018 is a Bloomberg backfill that tracks Fed Funds OIS almost exactly. The pre-2018 discount curve is a modelling choice, and the paper will say which one it uses.

### Rebuilding the files

The loader expects three workbooks in `data/`:

- `bbg_credit_pull_10_01_26.xlsx`: sheets `HYG`, `LQD`, `JNK`, `Other Series`
- `bbg_cdx_indices.xlsx`: sheets `CDX Core`, `CDX Curve`, `iTraxx`
- `bbg_rates_curve.xlsx`: sheets `SOFR OIS`, `FF OIS`, `Treasury`

Each sheet holds one `BDH` block per series, side by side: up to three label rows (field ID, then a description), a `Date` / `Value` header, then the data. Paste values before saving so the file opens without the terminal. The exact labels the loader matches on are in [`credit_engine/data/catalog.py`](credit_engine/data/catalog.py).

`data/` is gitignored, along with every spreadsheet, CSV, parquet and pickle file, so pulls can't get committed by accident (to protect BBG licensing).

## Usage

```bash
pip install -e ".[dev]"
python -m credit_engine.data.loader   # parse the pulls, cache to data/processed/
pytest
```

```python
from credit_engine.data import load_panel, load_series

hy_spread = load_series("cdx_hy_5y.spread")
skew = load_panel(["hyg.ivol_30d_90", "hyg.ivol_30d_100", "hyg.ivol_30d_110"])
```

The tests build a synthetic workbook, so they run without any Bloomberg data.
