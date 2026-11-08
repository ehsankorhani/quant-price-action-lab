"""Three Core Quantified Price Action + Volume/AVWAP Strategies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pa_bot.indicators import BarContext


@dataclass(frozen=True)
class Signal:
    """Trade entry signal emitted at the close of bar `idx`."""

    strategy_name: str
    idx: int
    date: str
    entry_price: float
    stop_loss: float
    target_price: float
    target_r: float
    max_hold_bars: int
    reason: str


class StrategyBase:
    """Base interface for Price Action swing strategies."""

    name: str = "Base"

    def __init__(self, use_volume_avwap: bool = True) -> None:
        self.use_volume_avwap = use_volume_avwap

    def evaluate(self, contexts: List[BarContext], idx: int) -> Optional[Signal]:
        raise NotImplementedError


class TrendPullbackStrategy(StrategyBase):
    """
    Archetype 1: Trend Pullback to Structure + Anchored VWAP (AVWAP).
    - Context: Confirmed uptrend (Close > SMA50 >= SMA200).
    - Setup: 2+ bar pullback into structural support / SMA20 / Swing-Low AVWAP.
    - Trigger: Bullish expansion/rejection bar closing in top 35% of range & breaking prior bar's high.
    - Volume/AVWAP Filter: Holds/reclaims Swing-Low AVWAP + dry-up on pullback or RVOL expansion on trigger.
    """

    def __init__(self, use_volume_avwap: bool = True, target_r: float = 2.5) -> None:
        super().__init__(use_volume_avwap=use_volume_avwap)
        self.target_r = target_r
        self.name = (
            "1. Trend Pullback (PA + AVWAP/Vol)"
            if use_volume_avwap
            else "1. Trend Pullback (Pure PA)"
        )

    def evaluate(self, contexts: List[BarContext], idx: int) -> Optional[Signal]:
        if idx < 55:
            return None

        ctx = contexts[idx]
        prev = contexts[idx - 1]
        prev2 = contexts[idx - 2]
        b = ctx.bar
        atr = ctx.atr_14

        # 1. Structural Uptrend Filter
        if not ctx.is_structural_uptrend:
            return None

        # 2. Pullback Setup: Recent 2-3 bars pulled back into value zone (near SMA20 or AVWAP)
        pulled_back = (
            prev.bar.low < prev2.bar.low
            or prev.bar.close < prev2.bar.close
        )
        near_value_zone = min(b.low, prev.bar.low) <= max(ctx.sma_20, ctx.avwap_swing_low) + 0.35 * atr
        if not (pulled_back and near_value_zone):
            return None

        # 3. Price Action Trigger: Bullish bar reclaiming prior bar high with strong close
        is_reversal_trigger = (
            b.is_bullish
            and b.close > prev.bar.high
            and b.close_position >= 0.65
            and b.range >= 0.60 * atr
        )
        if not is_reversal_trigger:
            return None

        # 4. Volume & Anchored VWAP Confirmation
        if self.use_volume_avwap:
            # Must close above Swing-Low AVWAP and Rolling 20-bar VWAP
            avwap_support = (
                b.close >= ctx.avwap_swing_low
                and b.close >= ctx.rolling_vwap_20 * 0.998
                and min(b.low, prev.bar.low) <= ctx.avwap_swing_low + 0.85 * atr
            )
            # Volume Price Analysis: seller exhaustion on pullback OR buyer expansion on trigger
            vpa_confirm = (
                (prev.rvol <= 0.90 and ctx.rvol >= 0.95)
                or ctx.rvol >= 1.15
            )
            if not (avwap_support and vpa_confirm):
                return None

        # Structural Stop Loss: below pullback low minus 0.25 ATR buffer
        pullback_low = min(b.low, prev.bar.low, prev2.bar.low)
        stop_loss = pullback_low - 0.25 * atr
        risk = b.close - stop_loss
        if risk <= 0.25 * atr or risk > 2.8 * atr:
            return None

        target_price = b.close + self.target_r * risk
        return Signal(
            strategy_name=self.name,
            idx=idx,
            date=b.date,
            entry_price=b.close,
            stop_loss=stop_loss,
            target_price=target_price,
            target_r=self.target_r,
            max_hold_bars=15,
            reason=(
                f"Pullback reclaim above {prev.bar.high:.2f} | "
                f"AVWAP={ctx.avwap_swing_low:.2f} | RVOL={ctx.rvol:.2f}x"
            ),
        )


class LiquiditySweepStrategy(StrategyBase):
    """
    Archetype 2: Liquidity Sweep / Failed Breakdown (Wyckoff Spring).
    - Context: Price in broad uptrend or range (Close > SMA200 * 0.97).
    - Setup: Intraday low sweeps BELOW a prior structural Swing Low / N-bar support level (running stops).
    - Trigger: Rejects breakdown and closes back ABOVE the support level in top 40% of range.
    - Volume/AVWAP Filter: Stopping/absorption volume (RVOL >= 1.10) + reclaims/holds Swing-Low AVWAP zone.
    """

    def __init__(self, use_volume_avwap: bool = True, target_r: float = 2.5) -> None:
        super().__init__(use_volume_avwap=use_volume_avwap)
        self.target_r = target_r
        self.name = (
            "2. Liquidity Sweep / Spring (PA + AVWAP/Vol)"
            if use_volume_avwap
            else "2. Liquidity Sweep / Spring (Pure PA)"
        )

    def evaluate(self, contexts: List[BarContext], idx: int) -> Optional[Signal]:
        if idx < 60:
            return None

        ctx = contexts[idx]
        b = ctx.bar
        atr = ctx.atr_14

        # Avoid catching falling knives in severe bear markets
        if b.close < ctx.sma_200 * 0.97 or ctx.sma_50 < ctx.sma_200 * 0.96:
            return None

        # Reference structural support: prior 10-to-3 bar low or confirmed Swing Low
        prior_window_low = min(contexts[k].bar.low for k in range(idx - 12, idx - 1))
        support_level = prior_window_low
        if ctx.swing_low_price is not None and abs(ctx.swing_low_price - prior_window_low) <= 1.0 * atr:
            support_level = max(prior_window_low, ctx.swing_low_price)

        # Sweep condition: Low pierces below support_level, but Close snaps back above it
        swept_support = (
            b.low < support_level - 0.03 * atr
            and b.low >= support_level - 1.25 * atr
            and b.close > support_level
        )
        if not swept_support:
            return None

        # Price Action Rejection: Strong close position or prominent lower rejection tail
        strong_rejection = (
            b.close_position >= 0.60
            and (b.is_bullish or b.lower_wick >= 0.45 * b.range)
        )
        if not strong_rejection:
            return None

        # Volume & AVWAP Filter: Institutional Stopping Volume absorbing the stop-run
        if self.use_volume_avwap:
            prev_rvol = contexts[idx - 1].rvol
            stopping_volume = ctx.rvol >= 1.10 or (prev_rvol >= 1.25 and ctx.rvol >= 0.95)
            avwap_reclaim = (
                b.close >= ctx.avwap_swing_low * 0.992
                and b.close > contexts[idx - 1].bar.close
            )
            if not (stopping_volume and avwap_reclaim):
                return None

        stop_loss = b.low - 0.25 * atr
        risk = b.close - stop_loss
        if risk <= 0.25 * atr or risk > 2.5 * atr:
            return None

        target_price = b.close + self.target_r * risk
        return Signal(
            strategy_name=self.name,
            idx=idx,
            date=b.date,
            entry_price=b.close,
            stop_loss=stop_loss,
            target_price=target_price,
            target_r=self.target_r,
            max_hold_bars=12,
            reason=(
                f"Swept support {support_level:.2f} (Low {b.low:.2f}) & reclaimed | "
                f"RVOL={ctx.rvol:.2f}x"
            ),
        )


class VolatilityContractionBreakoutStrategy(StrategyBase):
    """
    Archetype 3: Volatility Contraction Pattern (VCP / Tight Range) Breakout.
    - Context: Strong uptrend (Close > SMA50 > SMA200).
    - Setup: Volatility compresses over prior 5-10 bars (tight range coil).
    - Trigger: Wide-range expansion bar breaks and closes above 10-bar resistance ceiling.
    - Volume/AVWAP Filter: Quiet volume during coil + high RVOL (>= 1.20x) on breakout above AVWAP.
    """

    def __init__(self, use_volume_avwap: bool = True, target_r: float = 3.0) -> None:
        super().__init__(use_volume_avwap=use_volume_avwap)
        self.target_r = target_r
        self.name = (
            "3. Volatility Contraction Breakout (PA + AVWAP/Vol)"
            if use_volume_avwap
            else "3. Volatility Contraction Breakout (Pure PA)"
        )

    def evaluate(self, contexts: List[BarContext], idx: int) -> Optional[Signal]:
        if idx < 60:
            return None

        ctx = contexts[idx]
        b = ctx.bar
        atr = ctx.atr_14

        # 1. Strong Trend Alignment
        if not (b.close > ctx.sma_50 and ctx.sma_50 > ctx.sma_200):
            return None

        # 2. Volatility Contraction in prior 6 bars (excluding current breakout bar)
        coil_contexts = contexts[idx - 6 : idx]
        avg_coil_range = sum(c.bar.range for c in coil_contexts) / len(coil_contexts)
        coil_high = max(c.bar.high for c in contexts[idx - 10 : idx])
        coil_low = min(c.bar.low for c in coil_contexts)

        is_contracted = (
            avg_coil_range <= 0.95 * atr
            and (coil_high - coil_low) <= 3.6 * atr
        )
        if not is_contracted:
            return None

        # 3. Breakout Expansion Trigger
        is_breakout = (
            b.close > coil_high
            and b.is_bullish
            and b.close_position >= 0.70
            and 0.75 * atr <= b.range <= 1.85 * atr
        )
        if not is_breakout:
            return None

        # 4. Volume Expansion & AVWAP Alignment
        if self.use_volume_avwap:
            # Coil had volume dry-up, and breakout has institutional RVOL >= 1.15x above AVWAPs
            coil_dry_up = min(c.rvol for c in coil_contexts) <= 0.85
            breakout_vol_expansion = ctx.rvol >= 1.15
            above_avwaps = (
                b.close > ctx.avwap_swing_low
                and b.close > ctx.rolling_vwap_20
                and b.close >= ctx.avwap_swing_high
            )
            if not (coil_dry_up and breakout_vol_expansion and above_avwaps):
                return None

        # Structural stop loss below the breakout bar and prior tight bar low
        pivot_low = min(b.low, contexts[idx - 1].bar.low)
        stop_loss = pivot_low - 0.20 * atr
        risk = b.close - stop_loss
        if risk <= 0.25 * atr or risk > 2.4 * atr:
            return None

        target_price = b.close + self.target_r * risk
        return Signal(
            strategy_name=self.name,
            idx=idx,
            date=b.date,
            entry_price=b.close,
            stop_loss=stop_loss,
            target_price=target_price,
            target_r=self.target_r,
            max_hold_bars=18,
            reason=(
                f"VCP breakout > {coil_high:.2f} | CoilRange={avg_coil_range:.2f} | "
                f"RVOL={ctx.rvol:.2f}x"
            ),
        )
