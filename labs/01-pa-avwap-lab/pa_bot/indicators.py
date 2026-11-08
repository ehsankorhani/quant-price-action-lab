"""Quantified Price Action, Causal Market Structure, RVOL, and Anchored VWAP (AVWAP)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pa_bot.data import Bar


@dataclass(frozen=True)
class BarContext:
    """Enriched Price Action + Volume/AVWAP state at bar index `idx` (strictly causal, zero lookahead)."""

    idx: int
    bar: Bar
    atr_14: float
    sma_20: float
    sma_50: float
    sma_200: float
    vol_sma_20: float
    rvol: float
    rolling_vwap_20: float

    # Causal confirmed swing pivots known as of bar `idx` close
    swing_low_price: Optional[float]
    swing_low_idx: Optional[int]
    prev_swing_low_price: Optional[float]

    swing_high_price: Optional[float]
    swing_high_idx: Optional[int]
    prev_swing_high_price: Optional[float]

    # Anchored VWAPs from the active structural Swing Low and Swing High
    avwap_swing_low: float
    avwap_swing_high: float

    @property
    def is_structural_uptrend(self) -> bool:
        """Higher Highs & Higher Lows OR stacked institutional trend (Close > SMA50 > SMA200)."""
        hh_hl = (
            self.swing_high_price is not None
            and self.prev_swing_high_price is not None
            and self.swing_low_price is not None
            and self.prev_swing_low_price is not None
            and self.swing_high_price > self.prev_swing_high_price
            and self.swing_low_price > self.prev_swing_low_price
        )
        ma_trend = self.bar.close > self.sma_50 and self.sma_50 >= self.sma_200 * 0.99
        return ma_trend and (hh_hl or self.bar.close > self.avwap_swing_low)


def compute_context(
    bars: List[Bar],
    pivot_left: int = 5,
    pivot_right: int = 2,
) -> List[BarContext]:
    """Compute causal Price Action, Market Structure pivots, RVOL, and Anchored VWAPs for all bars."""
    n = len(bars)
    if n == 0:
        return []

    # Precompute cumulative (TypicalPrice * Volume) and cumulative Volume for O(1) AVWAP queries
    cum_tp_vol: List[float] = [0.0] * (n + 1)
    cum_vol: List[float] = [0.0] * (n + 1)
    for i, b in enumerate(bars):
        cum_tp_vol[i + 1] = cum_tp_vol[i] + b.typical_price * b.volume
        cum_vol[i + 1] = cum_vol[i] + b.volume

    def calc_avwap(start_idx: int, end_idx: int) -> float:
        vol_sum = cum_vol[end_idx + 1] - cum_vol[start_idx]
        if vol_sum <= 0:
            return bars[end_idx].typical_price
        return (cum_tp_vol[end_idx + 1] - cum_tp_vol[start_idx]) / vol_sum

    # True Range & Wilder's ATR(14)
    tr_list: List[float] = []
    atr_list: List[float] = []
    for i, b in enumerate(bars):
        if i == 0:
            tr = b.high - b.low
        else:
            prev_c = bars[i - 1].close
            tr = max(b.high - b.low, abs(b.high - prev_c), abs(b.low - prev_c))
        tr_list.append(tr)
        if i < 14:
            atr_list.append(sum(tr_list) / len(tr_list))
        else:
            atr_list.append((atr_list[-1] * 13.0 + tr) / 14.0)

    # Track confirmed causal Swing Highs and Swing Lows
    swing_low_price: Optional[float] = None
    swing_low_idx: Optional[int] = None
    prev_swing_low_price: Optional[float] = None

    swing_high_price: Optional[float] = None
    swing_high_idx: Optional[int] = None
    prev_swing_high_price: Optional[float] = None

    contexts: List[BarContext] = []

    for i, b in enumerate(bars):
        # Check if candidate bar `p = i - pivot_right` just got confirmed at bar `i`
        p = i - pivot_right
        if p >= pivot_left:
            cand_low = bars[p].low
            is_pivot_low = all(
                cand_low <= bars[k].low for k in range(p - pivot_left, p)
            ) and all(cand_low < bars[k].low for k in range(p + 1, i + 1))
            if is_pivot_low:
                prev_swing_low_price = swing_low_price
                swing_low_price = cand_low
                swing_low_idx = p

            cand_high = bars[p].high
            is_pivot_high = all(
                cand_high >= bars[k].high for k in range(p - pivot_left, p)
            ) and all(cand_high > bars[k].high for k in range(p + 1, i + 1))
            if is_pivot_high:
                prev_swing_high_price = swing_high_price
                swing_high_price = cand_high
                swing_high_idx = p

        # Moving averages
        c_slice_20 = [bars[k].close for k in range(max(0, i - 19), i + 1)]
        c_slice_50 = [bars[k].close for k in range(max(0, i - 49), i + 1)]
        c_slice_200 = [bars[k].close for k in range(max(0, i - 199), i + 1)]
        v_slice_20 = [bars[k].volume for k in range(max(0, i - 19), i + 1)]

        sma_20 = sum(c_slice_20) / len(c_slice_20)
        sma_50 = sum(c_slice_50) / len(c_slice_50)
        sma_200 = sum(c_slice_200) / len(c_slice_200)
        vol_sma_20 = sum(v_slice_20) / len(v_slice_20)
        rvol = b.volume / vol_sma_20 if vol_sma_20 > 0 else 1.0

        rolling_vwap_20 = calc_avwap(max(0, i - 19), i)
        avwap_low = (
            calc_avwap(swing_low_idx, i)
            if swing_low_idx is not None
            else rolling_vwap_20
        )
        avwap_high = (
            calc_avwap(swing_high_idx, i)
            if swing_high_idx is not None
            else rolling_vwap_20
        )

        contexts.append(
            BarContext(
                idx=i,
                bar=b,
                atr_14=atr_list[i],
                sma_20=sma_20,
                sma_50=sma_50,
                sma_200=sma_200,
                vol_sma_20=vol_sma_20,
                rvol=rvol,
                rolling_vwap_20=rolling_vwap_20,
                swing_low_price=swing_low_price,
                swing_low_idx=swing_low_idx,
                prev_swing_low_price=prev_swing_low_price,
                swing_high_price=swing_high_price,
                swing_high_idx=swing_high_idx,
                prev_swing_high_price=prev_swing_high_price,
                avwap_swing_low=avwap_low,
                avwap_swing_high=avwap_high,
            )
        )

    return contexts
