"""Event-driven swing backtester with slippage, gap-through-stop realism, and R-multiple analytics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from pa_bot.indicators import BarContext
from pa_bot.strategies import Signal, StrategyBase


@dataclass
class TradeRecord:
    """Completed swing trade with full R-multiple and dollar accounting."""

    symbol: str
    strategy: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    stop_loss: float
    target_price: float
    shares: int
    r_multiple: float
    pnl_dollars: float
    bars_held: int
    exit_reason: str
    signal_reason: str


@dataclass
class BacktestSummary:
    """Aggregated performance metrics across a symbol universe."""

    strategy_name: str
    total_trades: int
    wins: int
    losses: int
    win_rate_pct: float
    avg_win_r: float
    avg_loss_r: float
    expectancy_r: float
    total_r: float
    profit_factor: float
    max_drawdown_r: float
    starting_equity: float
    ending_equity: float
    total_return_pct: float
    trades: List[TradeRecord]


def run_backtest_on_symbol(
    symbol: str,
    contexts: List[BarContext],
    strategy: StrategyBase,
    slippage_bps: float = 5.0,
    move_to_breakeven_at_r: float = 1.5,
) -> List[TradeRecord]:
    """
    Simulate strategy on a single symbol's causal BarContext sequence.
    - Signal triggers at bar `i` close (MOC / near-close fill with slippage).
    - Next bars `i+1 ...` check overnight gaps, stop loss, profit target, breakevenratchet, and time stop.
    """
    slip_mult = slippage_bps / 10000.0
    trades: List[TradeRecord] = []
    i = 60
    n = len(contexts)

    while i < n - 1:
        sig: Signal | None = strategy.evaluate(contexts, i)
        if sig is None:
            i += 1
            continue

        entry_fill = sig.entry_price * (1.0 + slip_mult)
        initial_risk_per_share = entry_fill - sig.stop_loss
        if initial_risk_per_share <= 0:
            i += 1
            continue

        active_stop = sig.stop_loss
        target = sig.target_price
        exit_price = entry_fill
        exit_date = contexts[i].bar.date
        exit_reason = "TIME_STOP"
        exit_idx = i + 1

        for j in range(i + 1, min(n, i + 1 + sig.max_hold_bars)):
            bar = contexts[j].bar
            exit_idx = j
            exit_date = bar.date

            # 1. Check overnight gap below active stop loss (realistic gap slippage!)
            if bar.open <= active_stop:
                exit_price = bar.open * (1.0 - slip_mult)
                exit_reason = "STOP_GAP" if active_stop <= sig.stop_loss else "TRAIL_STOP_GAP"
                break

            # 2. Check intraday stop loss hit (conservative: check stop before target on same bar)
            if bar.low <= active_stop:
                exit_price = active_stop * (1.0 - slip_mult)
                exit_reason = "STOP_LOSS" if active_stop <= sig.stop_loss else "BREAKEVEN_STOP"
                break

            # 3. Check profit target hit
            if bar.high >= target:
                # If bar gapped above target on open, fill at open; otherwise at target
                raw_target_fill = max(bar.open, target)
                exit_price = raw_target_fill * (1.0 - slip_mult)
                exit_reason = "TARGET_HIT"
                break

            # 4. Ratchet stop to breakeven (+0.1R) if trade reaches +1.5R in favor by close
            unrealized_r = (bar.close - entry_fill) / initial_risk_per_share
            if unrealized_r >= move_to_breakeven_at_r and active_stop < entry_fill:
                active_stop = entry_fill + 0.10 * initial_risk_per_share

            # 5. Max hold period reached at bar close
            if j == min(n - 1, i + sig.max_hold_bars):
                exit_price = bar.close * (1.0 - slip_mult)
                exit_reason = "TIME_EXIT"
                break

        r_mult = (exit_price - entry_fill) / initial_risk_per_share
        trades.append(
            TradeRecord(
                symbol=symbol,
                strategy=strategy.name,
                entry_date=sig.date,
                exit_date=exit_date,
                entry_price=entry_fill,
                exit_price=exit_price,
                stop_loss=sig.stop_loss,
                target_price=target,
                shares=0,  # Populated during portfolio simulation
                r_multiple=r_mult,
                pnl_dollars=0.0,
                bars_held=exit_idx - i,
                exit_reason=exit_reason,
                signal_reason=sig.reason,
            )
        )

        # Advance index past trade exit so we never overlap positions in the same symbol
        i = exit_idx + 1

    return trades


def evaluate_portfolio(
    strategy: StrategyBase,
    universe_contexts: Dict[str, List[BarContext]],
    starting_equity: float = 100_000.0,
    risk_per_trade_pct: float = 0.01,
    slippage_bps: float = 5.0,
) -> BacktestSummary:
    """Run strategy across all symbols, sort trades chronologically, and compute portfolio metrics."""
    all_trades: List[TradeRecord] = []
    for symbol, contexts in universe_contexts.items():
        sym_trades = run_backtest_on_symbol(
            symbol=symbol,
            contexts=contexts,
            strategy=strategy,
            slippage_bps=slippage_bps,
        )
        all_trades.extend(sym_trades)

    # Sort chronologically by entry_date then exit_date
    all_trades.sort(key=lambda t: (t.entry_date, t.exit_date, t.symbol))

    equity = starting_equity
    cum_r = 0.0
    peak_r = 0.0
    max_dd_r = 0.0

    wins_r: List[float] = []
    losses_r: List[float] = []
    gross_profit_r = 0.0
    gross_loss_r = 0.0

    for t in all_trades:
        risk_dollars = equity * risk_per_trade_pct
        per_share_risk = max(t.entry_price - t.stop_loss, 1e-6)
        shares = max(1, int(risk_dollars // per_share_risk))
        pnl = shares * (t.exit_price - t.entry_price)

        t.shares = shares
        t.pnl_dollars = pnl
        equity += pnl

        cum_r += t.r_multiple
        if cum_r > peak_r:
            peak_r = cum_r
        dd_r = peak_r - cum_r
        if dd_r > max_dd_r:
            max_dd_r = dd_r

        if t.r_multiple > 0:
            wins_r.append(t.r_multiple)
            gross_profit_r += t.r_multiple
        else:
            losses_r.append(t.r_multiple)
            gross_loss_r += abs(t.r_multiple)

    total = len(all_trades)
    win_count = len(wins_r)
    loss_count = len(losses_r)
    win_rate = (win_count / total * 100.0) if total > 0 else 0.0
    avg_win_r = (sum(wins_r) / win_count) if win_count > 0 else 0.0
    avg_loss_r = (sum(losses_r) / loss_count) if loss_count > 0 else 0.0
    expectancy_r = (cum_r / total) if total > 0 else 0.0
    pf = (gross_profit_r / gross_loss_r) if gross_loss_r > 0 else float("inf")
    ret_pct = (equity - starting_equity) / starting_equity * 100.0

    return BacktestSummary(
        strategy_name=strategy.name,
        total_trades=total,
        wins=win_count,
        losses=loss_count,
        win_rate_pct=win_rate,
        avg_win_r=avg_win_r,
        avg_loss_r=avg_loss_r,
        expectancy_r=expectancy_r,
        total_r=cum_r,
        profit_factor=pf,
        max_drawdown_r=max_dd_r,
        starting_equity=starting_equity,
        ending_equity=equity,
        total_return_pct=ret_pct,
        trades=all_trades,
    )
