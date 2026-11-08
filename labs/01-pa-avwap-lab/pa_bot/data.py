"""Market data fetcher and local CSV cache for US Stocks & ETFs."""

from __future__ import annotations

import csv
import datetime as dt
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class Bar:
    """Single OHLCV price bar."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def typical_price(self) -> float:
        """Institutional Typical Price (H + L + C) / 3 used in VWAP/AVWAP."""
        return (self.high + self.low + self.close) / 3.0

    @property
    def body(self) -> float:
        """Absolute candle body size |Close - Open|."""
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        """Total bar range (High - Low)."""
        return max(self.high - self.low, 1e-9)

    @property
    def upper_wick(self) -> float:
        """Upper shadow length."""
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        """Lower shadow (rejection tail) length."""
        return min(self.open, self.close) - self.low

    @property
    def close_position(self) -> float:
        """Where the close sits inside the bar's range: 0.0 = Low, 1.0 = High."""
        if self.high <= self.low:
            return 0.5
        return (self.close - self.low) / (self.high - self.low)

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def fetch_ohlcv(
    symbol: str,
    interval: str = "1d",
    period_range: str = "5y",
    use_cache: bool = True,
) -> List[Bar]:
    """Fetch historical OHLCV bars from Yahoo Finance v8 API with local CSV caching."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = DATA_DIR / f"{symbol.upper()}_{interval}_{period_range}.csv"

    if use_cache and cache_file.exists():
        return _read_csv(cache_file)

    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}"
        f"?interval={interval}&range={period_range}&includeAdjustedClose=true"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]

    opens = quote["open"]
    highs = quote["high"]
    lows = quote["low"]
    closes = quote["close"]
    volumes = quote["volume"]

    bars: List[Bar] = []
    for ts, o, h, l, c, v in zip(timestamps, opens, highs, lows, closes, volumes):
        if None in (o, h, l, c, v) or v <= 0:
            continue
        date_str = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).strftime(
            "%Y-%m-%d" if interval == "1d" else "%Y-%m-%d %H:%M"
        )
        bars.append(
            Bar(
                date=date_str,
                open=float(o),
                high=float(h),
                low=float(l),
                close=float(c),
                volume=float(v),
            )
        )

    _write_csv(cache_file, bars)
    return bars


def _write_csv(path: Path, bars: List[Bar]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "high", "low", "close", "volume"])
        for b in bars:
            writer.writerow(
                [
                    b.date,
                    f"{b.open:.4f}",
                    f"{b.high:.4f}",
                    f"{b.low:.4f}",
                    f"{b.close:.4f}",
                    f"{b.volume:.0f}",
                ]
            )


def _read_csv(path: Path) -> List[Bar]:
    bars: List[Bar] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bars.append(
                Bar(
                    date=row["date"],
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )
    return bars
