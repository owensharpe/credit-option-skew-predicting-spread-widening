"""
Name: catalog.py
Author: Owen Sharpe
Description: every series the engine uses: where it lives in the pull and what it is. Matching on the labels printed above each block, rather than on column position, means a reordered or extended sheet still loads correctly, and a renamed label fails loudly instead of silently loading the wrong series. `verified` is True when the Bloomberg ticker is recorded in the pull workbook itself. The rest follow the standard Bloomberg naming for that instrument but were not written down at pull time; check them in SECF before re-pulling.
"""

from __future__ import annotations

from dataclasses import dataclass

# global variables
CREDIT_PULL = "bbg_credit_pull_10_01_26.xlsx"
CDX_PULL = "bbg_cdx_indices.xlsx"
RATES_PULL = "bbg_rates_curve.xlsx"

@dataclass(frozen=True)
class SeriesSpec:
    name: str
    workbook: str
    sheet: str
    labels: tuple[str, ...]
    ticker: str
    field: str
    units: str
    verified: bool = True

# credit ETFs: option implied vol, price and fund data.

_ETF_FIELDS = [
    # (name suffix, field, description label in the sheet, units)
    ("ivol_1m_100", "VL130", "1M IVOL @ 100% mny", "vol %"),
    ("ivol_30d_100", "VL137", "30D IVOL @ 100% mny", "vol %"),
    ("ivol_30d_90", "VL140", "30D IVOL @ 90% mny", "vol %"),
    ("ivol_30d_110", "VL134", "30D IVOL @ 110% mny", "vol %"),
    ("ivol_60d_100", "VL151", "60D IVOL @ 100% mny", "vol %"),
    ("ivol_6m_100", "VL165", "6M IVOL @ 100% mny", "vol %"),
    ("ivol_6m_90", "VL168", "6M IVOL @ 90% mny", "vol %"),
    ("ivol_6m_110", "VL162", "6M IVOL @ 110% mny", "vol %"),
    ("ivol_24m_100", "VL186", "24M IVOL @ 100% mny", "vol %"),
    ("ivol_1m_call_25d", "RK903", "1M Call IVOL 25 delta", "vol %"),
    ("px_last", "PX_LAST", "Close price", "USD"),
    ("volume", "PX_VOLUME", "Share volume", "shares"),
    ("nav", "FUND_NET_ASSET_VAL", "NAV", "USD"),
    ("shares_out", "EQY_SH_OUT", "Shares outstanding", "millions of shares"),
    ("rvol_30d", "VOLATILITY_30D", "Realized vol 30d", "vol %"),
    ("rvol_90d", "VOLATILITY_90D", "Realized vol 90d", "vol %"),
]

_ETFS = [
    spec
    for etf in ("HYG", "LQD", "JNK")
    for spec in (
        SeriesSpec(
            name=f"{etf.lower()}.{suffix}",
            workbook=CREDIT_PULL,
            sheet=etf,
            labels=(field, label),
            ticker=f"{etf} US Equity",
            field=field,
            units=units,
        )
        for suffix, field, label, units in _ETF_FIELDS
    )
]

# CDX and iTraxx. generic (GEN) tickers roll to the on-the-run series, which is what gives them history back past the current series' roll date.

def _cdx(name, sheet, labels, ticker, field="PX_LAST", units="bp", verified=True):
    return SeriesSpec(name, CDX_PULL, sheet, labels, ticker, field, units, verified)

_CDX = [
    _cdx("cdx_hy_5y.price", "CDX Core", ("HY 5Y", "PRICE"),
         "CDX HY CDSI GEN 5Y PRC Corp", units="price per 100"),
    _cdx("cdx_hy_5y.spread", "CDX Core", ("HY 5Y", "SPREAD"),
         "CDX HY CDSI GEN 5Y SPRD Corp"),
    _cdx("cdx_ig_5y.spread", "CDX Core", ("IG 5Y", "SPREAD"),
         "CDX IG CDSI GEN 5Y Corp"),
    _cdx("cdx_ig_3y.spread", "CDX Curve", ("IG 3Y", "SPREAD"),
         "CDX IG CDSI GEN 3Y Corp", verified=False),
    _cdx("cdx_ig_7y.spread", "CDX Curve", ("IG 7Y", "SPREAD"),
         "CDX IG CDSI GEN 7Y Corp"),
    _cdx("cdx_ig_10y.spread", "CDX Curve", ("IG 10Y", "SPREAD"),
         "CDX IG CDSI GEN 10Y Corp"),
    _cdx("cdx_hy_7y.spread", "CDX Curve", ("HY 7Y", "SPREAD"),
         "CDX HY CDSI GEN 7Y SPRD Corp", verified=False),
    _cdx("cdx_hy_3y.price", "CDX Curve", ("HY 3Y", "PRICE"),
         "CDX HY CDSI GEN 3Y PRC Corp", units="price per 100", verified=False),
    _cdx("cdx_hy_7y.price", "CDX Curve", ("HY 7Y", "PRICE"),
         "CDX HY CDSI GEN 7Y PRC Corp", units="price per 100", verified=False),
    _cdx("itraxx_main_5y.spread", "iTraxx", ("Main 5Y", "SPREAD"),
         "ITRX EUR CDSI GEN 5Y Corp"),
    _cdx("itraxx_main_10y.spread", "iTraxx", ("Main 10Y", "SPREAD"),
         "ITRX EUR CDSI GEN 10Y Corp", verified=False),
    _cdx("itraxx_snrfin_5y.spread", "iTraxx", ("Snr Fin 5Y", "SPREAD"),
         "ITRX EUR SNRFIN CDSI GEN 5Y Corp", verified=False),
]

# equity controls

_CONTROLS = [
    SeriesSpec("spy.ivol_30d_100", CREDIT_PULL, "Other Series",
               ("VL137", "SPY 30D IVOL @ 100% - equity control"),
               "SPY US Equity", "VL137", "vol %", verified=False),
    SeriesSpec("spy.ivol_30d_90", CREDIT_PULL, "Other Series",
               ("VL140", "SPY 30D IVOL @ 90% - equity control"),
               "SPY US Equity", "VL140", "vol %", verified=False),
    SeriesSpec("spy.ivol_30d_110", CREDIT_PULL, "Other Series",
               ("VL134", "SPY 30D IVOL @ 110% - equity control"),
               "SPY US Equity", "VL134", "vol %", verified=False),
    SeriesSpec("vix.px_last", CREDIT_PULL, "Other Series", ("PX_LAST", "VIX"),
               "VIX Index", "PX_LAST", "vol %", verified=False),
    SeriesSpec("spx.px_last", CREDIT_PULL, "Other Series", ("PX_LAST", "S&P 500"),
               "SPX Index", "PX_LAST", "index points", verified=False),
]

# rates. SOFR OIS is the discount curve from 2018; Fed Funds OIS is the pre-2018 fallback. Treasuries are controls only, never used for discounting. Sub-year tenor letters: A=1M, B=2M, C=3M, F=6M, I=9M.

_SOFR = [("1M", "A"), ("2M", "B"), ("3M", "C"), ("6M", "F"), ("9M", "I"),
         ("1Y", "1"), ("2Y", "2"), ("3Y", "3"), ("4Y", "4"), ("5Y", "5"),
         ("7Y", "7"), ("10Y", "10")]
_FF = [("1M", "A"), ("3M", "C"), ("6M", "F"), ("1Y", "1"), ("2Y", "2"),
       ("3Y", "3"), ("5Y", "5"), ("7Y", "7"), ("10Y", "10")]
_UST = [("3M", "USGG3M Index"), ("2Y", "USGG2YR Index"), ("5Y", "USGG5YR Index"),
        ("10Y", "USGG10YR Index"), ("30Y", "USGG30YR Index")]

_RATES = (
    [
        SeriesSpec(f"sofr_ois.{tenor.lower()}", RATES_PULL, "SOFR OIS",
                   (tenor, "SOFR OIS"), f"USOSFR{code} Curncy", "PX_LAST", "%",
                   verified=code in {"1", "5", "10"})
        for tenor, code in _SOFR
    ]
    + [
        SeriesSpec(f"ff_ois.{tenor.lower()}", RATES_PULL, "FF OIS",
                   (tenor, "FF OIS"), f"USSO{code} Curncy", "PX_LAST", "%",
                   verified=code == "5")
        for tenor, code in _FF
    ]
    + [
        SeriesSpec(f"ust.{tenor.lower()}", RATES_PULL, "Treasury",
                   (tenor, "UST yield"), ticker, "PX_LAST", "%",
                   verified=tenor == "5Y")
        for tenor, ticker in _UST
    ]
    + [
        SeriesSpec("ust.2s10s", RATES_PULL, "Treasury", ("2s10s", "Slope"),
                   "USYC2Y10 Index", "PX_LAST", "bp", verified=False),
    ]
)

CATALOG: dict[str, SeriesSpec] = {
    spec.name: spec for spec in _ETFS + _CDX + _CONTROLS + _RATES
}

# pulled but I deliberately left out so nobody adds them back by accident:
# - CDX Core "SPREAD (iBoxx)" cross-checks: identical to the CDX spread columns on every row, so they are a second copy and not an independent check.
# - Other Series CDX HY/IG 5Y and 2Y/10Y Treasury: duplicates of CDX Core and the Treasury sheet.
# - CDX HY 3Y spread, iTraxx Crossover: the pulls returned nothing.
# - CDX HY 10Y spread/price: nine observations in Dec 2022.
# - bbg_vol_surface (WIP).xlsx: the moneyness grid returned #N/A throughout.
