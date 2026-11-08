#!/usr/bin/env python3
"""
Price Action & Volume/AVWAP Strategy Comparison Lab.
Fetches 5 years of Daily OHLCV data for liquid US Stocks & ETFs and compares:
  1. Trend Pullback to Structure (+ AVWAP/RVOL vs Pure PA)
  2. Liquidity Sweep / Wyckoff Spring (+ AVWAP/RVOL vs Pure PA)
  3. Volatility Contraction (VCP) Breakout (+ AVWAP/RVOL vs Pure PA)
"""

from __future__ import annotations

import argparse
from typing import Dict, List

from pa_bot.backtest import BacktestSummary, evaluate_portfolio
from pa_bot.data import fetch_ohlcv
from pa_bot.indicators import BarContext, compute_context
from pa_bot.strategies import (
    LiquiditySweepStrategy,
    StrategyBase,
    TrendPullbackStrategy,
    VolatilityContractionBreakoutStrategy,
)

DEFAULT_UNIVERSE = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "AMZN", "META"]


def load_universe(symbols: List[str], interval: str = "1d", period: str = "5y") -> Dict[str, List[BarContext]]:
    universe_contexts: Dict[str, List[BarContext]] = {}
    for sym in symbols:
        bars = fetch_ohlcv(sym, interval=interval, period_range=period, use_cache=True)
        universe_contexts[sym] = compute_context(bars)
    return universe_contexts


def print_summary_table(summaries: List[BacktestSummary]) -> None:
    header = (
        f"{'Strategy':<45} | {'Trades':>6} | {'Win%':>6} | "
        f"{'AvgWin':>7} | {'AvgLoss':>7} | {'Exp(R)':>7} | "
        f"{'Tot R':>7} | {'PF':>5} | {'MaxDD(R)':>8}"
    )
    print("\n" + "=" * len(header))
    print(header)
    print("-" * len(header))
    for s in summaries:
        print(
            f"{s.strategy_name:<45} | {s.total_trades:>6d} | {s.win_rate_pct:>5.1f}% | "
            f"{s.avg_win_r:>+6.2f}R | {s.avg_loss_r:>+6.2f}R | {s.expectancy_r:>+6.2f}R | "
            f"{s.total_r:>+6.1f}R | {s.profit_factor:>5.2f} | {s.max_drawdown_r:>7.1f}R"
        )
    print("=" * len(header))


def print_sample_trades(summary: BacktestSummary, count: int = 4) -> None:
    print(f"\nRecent Sample Trades — {summary.strategy_name}:")
    for t in summary.trades[-count:]:
        print(
            f"  [{t.symbol:<4}] {t.entry_date} -> {t.exit_date} ({t.bars_held:>2d}d) | "
            f"Entry: ${t.entry_price:>7.2f} | Stop: ${t.stop_loss:>7.2f} | Exit: ${t.exit_price:>7.2f} | "
            f"{t.r_multiple:>+5.2f}R ({t.exit_reason}) | {t.signal_reason}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Price Action & Volume/AVWAP Strategy Lab")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=DEFAULT_UNIVERSE,
        help="List of US stock/ETF tickers to test",
    )
    parser.add_argument("--interval", default="1d", help="Bar interval (1d or 1h)")
    parser.add_argument("--period", default="5y", help="Lookback range (e.g. 5y, 2y)")
    args = parser.parse_args()

    print(f"Loading {args.period} ({args.interval}) market data for: {', '.join(args.symbols)}...")
    universe = load_universe(args.symbols, interval=args.interval, period=args.period)
    for sym, ctxs in universe.items():
        print(f"  {sym:<5}: {len(ctxs)} bars ({ctxs[0].bar.date} -> {ctxs[-1].bar.date})")

    strategies: List[StrategyBase] = [
        TrendPullbackStrategy(use_volume_avwap=True),
        TrendPullbackStrategy(use_volume_avwap=False),
        LiquiditySweepStrategy(use_volume_avwap=True),
        LiquiditySweepStrategy(use_volume_avwap=False),
        VolatilityContractionBreakoutStrategy(use_volume_avwap=True),
        VolatilityContractionBreakoutStrategy(use_volume_avwap=False),
    ]

    summaries = [evaluate_portfolio(strat, universe) for strat in strategies]
    print_summary_table(summaries)

    for s in summaries:
        if "PA + AVWAP/Vol" in s.strategy_name:
            print_sample_trades(s, count=3)


if __name__ == "__main__":
    main()
