# Module 4: Event-Driven Execution Realism & $R$-Multiple Risk Engine

**Code Reference:** [`labs/01-pa-avwap-lab/pa_bot/backtest.py`](../labs/01-pa-avwap-lab/pa_bot/backtest.py)

Most toy backtesters wildly overestimate returns because they assume frictionless fills at exact stop prices and allow overlapping lookahead trades. `pa_bot/backtest.py` enforces institutional execution realism.

---

## 4.1 Execution Path Pathology & Anti-Cheat Rules (`backtest.py:57-120`)

### 1. Entry Slippage (`backtest.py:72`)
With `slippage_bps = 5.0` ($0.05\%$ per side), buying at bar $i$ close fills slightly worse than the printed close:
$$\text{EntryFill} = \text{SignalPrice} \times (1 + 0.0005)$$
And initial per-share risk ($1R$) is measured from the **actual slipped entry fill**, not the theoretical close:
$$\text{InitialRiskPerShare} = \text{EntryFill} - \text{StopLoss}$$

### 2. Overnight Gap-Through-Stop Pathology (`STOP_GAP`, `backtest.py:88-91`)
In swing trading US Stocks & ETFs, bad news or macro shocks happen overnight. If your active stop loss is $\$100.00$ and the stock gaps open at $\$96.00$ the next morning, **your stop-loss order becomes a market order at the open**—you get filled at $\$96.00$ minus slippage, NOT $\$100.00$:

```python
# pa_bot/backtest.py:88-91
if bar.open <= active_stop:
    exit_price = bar.open * (1.0 - slip_mult)
    exit_reason = "STOP_GAP" if active_stop <= sig.stop_loss else "TRAIL_STOP_GAP"
    break
```
* This is why you occasionally see losses of `-1.12R` or `-1.18R` in the trade log (e.g., `[SPY] 2026-02-20 -> 2026-03-02 | -1.12R (STOP_GAP)`), and why AvgLoss is roughly `-0.95R` to `-1.05R` instead of an artificial `-1.00R`.

### 3. Intrabar Conservative Precedence (`backtest.py:93-105`)
On daily OHLC bars, if a wild bar's `low <= active_stop` AND its `high >= target`, we do not know whether the low or high happened first intraday.
* **Conservative Rule:** `backtest.py` checks the stop loss (`bar.low <= active_stop`) **before** checking the profit target (`bar.high >= target`). An honest backtester always resolves intrabar ambiguity against the trader.

---

## 4.2 Dynamic Trade Management (`backtest.py:107-120`)

### 1. The $+1.5R$ Breakeven Ratchet (`backtest.py:108-110`)
Never let a swing trade that reached $+1.5R$ at a daily close turn back into a $-1.0R$ loser:

```python
# pa_bot/backtest.py:108-110
unrealized_r = (bar.close - entry_fill) / initial_risk_per_share
if unrealized_r >= move_to_breakeven_at_r and active_stop < entry_fill:
    active_stop = entry_fill + 0.10 * initial_risk_per_share
```
* Notice we waits for $+1.5R$ (not $+0.5R$ or $+1.0R$), and ratchets to $+0.10R$ to cover round-trip slippage. Moving stops to breakeven too early (e.g., at $+0.75R$) chokes winners during normal trend digestion.

### 2. Time Stops (`TIME_EXIT`, `backtest.py:113-116`)
Each setup defines a `max_hold_bars` horizon ($12\text{–}18$ trading days). If a setup hasneither hit its target nor its stop within 3 weeks, the initial catalyst has dissipated—the position is closed at `bar.close * (1 - slip_mult)` to free capital and eliminate dead-money exposure.

---

## 4.3 Portfolio Position Sizing & $R$-Multiple Analytics (`backtest.py:143-225`)

### Fixed-Fractional Risk Position Sizing (`backtest.py:173-176`)
Professional traders never buy a fixed number of shares (e.g., "100 shares") or a fixed dollar amount (e.g., "\$10,000 per trade"). Instead, every trade risks a fixed fraction of current account equity ($\text{Risk\%} = 1.0\%$):

$$\text{RiskDollars} = \text{Equity} \times 0.01$$

$$\text{Shares} = \left\lfloor \frac{\text{RiskDollars}}{\text{EntryFill} - \text{StopLoss}} \right\rfloor$$

* **Wide stop ($5\%$ away):** Automatically buys fewer shares so a stop-out still loses only $1\%$ of equity ($-1R$).
* **Tight VCP stop ($1.5\%$ away):** Automatically scales share count up so a $+2.5R$ target nets $+2.5\%$ on total account equity.

### Core System Health Metrics
1. **Expectancy ($E_R$):** Average $R$-multiple netted per trade after slippage and gaps:
   $$E_R = \frac{1}{N}\sum_{k=1}^{N} R_k = (\text{WinRate} \times \text{AvgWin}_R) - (\text{LossRate} \times |\text{AvgLoss}_R|)$$
2. **Profit Factor ($\text{PF}$):** Gross winning $R$ divided by gross losing $R$:
   $$\text{PF} = \frac{\sum_{R_k > 0} R_k}{\sum_{R_k \le 0} |R_k|}$$
   * $\text{PF} < 1.0$: Losing system.
   * $\text{PF} \in [1.3, 1.6]$: Solid institutional swing system.
   * $\text{PF} > 1.8$: High-edge selective system (like our VCP + AVWAP/VPA at $\text{PF} = 2.11$).
3. **Max Drawdown in $R$ ($\text{MaxDD}_R$):** Worst peak-to-trough decline in cumulative $R$. If $\text{MaxDD}_R = 5.8R$ and you risk $1\%$ per trade, your worst historical equity drawdown was roughly $5.8\%$.

---

## Mastery Gate 4 (Self-Check)

You have a $\$50,000$ account and risk $1.0\%$ per trade. Today at market close, `VolatilityContractionBreakoutStrategy` triggers on `NVDA` at $\text{EntryFill} = \$240.00$ with a structural stop loss at $\text{StopLoss} = \$232.00$ and a $3.0R$ target.
1. What is your dollar risk ($1R$) on the trade?
2. How many shares does the bot buy?
3. What is the exact target price, and at what daily closing price will the bot ratchet your stop loss to breakeven ($+0.10R$)?
