# Module 3: The Three Core Algorithmic Price Action Setups

**Code Reference:** [`labs/01-pa-avwap-lab/pa_bot/strategies.py`](../labs/01-pa-avwap-lab/pa_bot/strategies.py)

Every profitable algorithmic price action strategy requires four non-negotiable components:
1. **Regime / Context Filter:** Is the macro auction aligned with our direction?
2. **Location (Setup):** Is price interacting with an asymmetric institutional reference level (Structure, AVWAP, or Tight Coil)?
3. **Trigger + VPA Confirmation:** Did buyers prove control on the current bar via price geometry ($\text{CP}_t$) and volume ($\text{RVOL}_t$)?
4. **Structural Invalidation (Stop Loss):** Where is the trade premise mathematically proven wrong?

---

## 3.1 Archetype 1: Trend Pullback to Structure + AVWAP (`TrendPullbackStrategy`)
**Code:** `pa_bot/strategies.py:35-126`

### The Institutional Thesis
In a healthy uptrend, price advances in impulse waves and digests gains via controlled 2–5 bar pullbacks toward institutional cost basis (`avwap_swing_low` and `sma_20`). Chasing extended impulse highs yields poor risk-reward; buying the **first bullish reclaim bar** off the AVWAP value zone provides a tight structural stop right under the pullback low.

### Exact Algorithmic Rules
1. **Regime (`strategies.py:61`):** `ctx.is_structural_uptrend == True` ($C_t > \text{SMA}_{50} \ge 0.99 \times \text{SMA}_{200}$ and either $HH+HL$ or $C_t > \text{AVWAP}_{\text{SL}}$).
2. **Pullback into Value Zone (`strategies.py:65-71`):**
   * Prior bars pulled back ($L_{t-1} < L_{t-2}$ or $C_{t-1} < C_{t-2}$).
   * Pullback low tested within $0.35\text{ ATR}$ of the value zone ceiling $\max(\text{SMA}_{20}, \text{AVWAP}_{\text{SL}})$.
3. **Price Action Trigger (`strategies.py:74-81`):**
   * Bullish bar ($C_t > O_t$) that breaks above yesterday's high ($C_t > H_{t-1}$), breaking the downward bar-by-bar pullback sequence.
   * Strong close in top $35\%$ of bar range ($\text{CP}_t \ge 0.65$) with meaningful range ($\text{Range}_t \ge 0.60\text{ ATR}$).
4. **AVWAP & Volume Confirmation (`strategies.py:84-97`):**
   * Closes above both `avwap_swing_low` and `rolling_vwap_20`.
   * Either sellers dried up on the prior pullback bar ($\text{RVOL}_{t-1} \le 0.90$ and $\text{RVOL}_t \ge 0.95$) **or** buyers expanded volume on the trigger bar ($\text{RVOL}_t \ge 1.15$).
5. **Structural Stop & Target (`strategies.py:100-106`):**
   * $\text{StopLoss} = \min(L_t, L_{t-1}, L_{t-2}) - 0.25\text{ ATR}$.
   * $\text{Target} = \text{Entry} + 2.5R$ (`max_hold_bars = 15`).

---

## 3.2 Archetype 2: Liquidity Sweep / Wyckoff Spring (`LiquiditySweepStrategy`)
**Code:** `pa_bot/strategies.py:129-212`

### The Institutional Thesis
Retail traders place stop-loss orders just below visible Swing Lows and N-bar support levels. When an institutional fund wants to buy a large position without pushing the ask price up against itself, it waits for (or pushes) price just below that support level. The triggered retail sell-stops provide a pool of liquidity that institutions absorb with passive limit buy orders, driving price back above support by the close (**Failed Breakdown / Wyckoff Spring**).

### Exact Algorithmic Rules
1. **Macro Crash Filter (`strategies.py:155`):** $C_t \ge 0.97 \times \text{SMA}_{200}$ and $\text{SMA}_{50} \ge 0.96 \times \text{SMA}_{200}$ (never buy breakdowns in a collapsing secular bear market).
2. **Support Level Identification (`strategies.py:159-162`):**
   * Reference support is the prior 12-to-2 bar window low (`min(low[idx-12 : idx-1])`), aligned with `swing_low_price` if within $1.0\text{ ATR}$.
3. **The Sweep & Snapback (`strategies.py:165-171`):**
   * Intraday low pierces below `support_level` by at least $0.03\text{ ATR}$ (up to $1.25\text{ ATR}$ max depth so it's a sweep, not a structural collapse).
   * By the close, price snaps back **above** `support_level` ($C_t > \text{support\_level}$).
4. **Rejection Geometry (`strategies.py:174-179`):**
   * $\text{CP}_t \ge 0.60$ and either bullish body ($C_t > O_t$) or deep lower tail ($\text{LowerWick}_t \ge 0.45 \times \text{Range}_t$).
5. **Stopping Volume & AVWAP Reclaim (`strategies.py:182-190`):**
   * **Stopping Volume:** $\text{RVOL}_t \ge 1.10$ (or prior washout bar had $\text{RVOL}_{t-1} \ge 1.25$ with follow-through $\text{RVOL}_t \ge 0.95$).
   * **AVWAP Reclaim:** $C_t \ge 0.992 \times \text{AVWAP}_{\text{SL}}$ and $C_t > C_{t-1}$.
6. **Structural Stop & Target (`strategies.py:192-197`):**
   * $\text{StopLoss} = L_t - 0.25\text{ ATR}$ (directly below the sweep wick tip).
   * $\text{Target} = \text{Entry} + 2.5R$ (`max_hold_bars = 12`).

> **Why Pure PA Fails on Sweeps:** In our 5-year test, trading Liquidity Sweeps *without* the Stopping Volume + AVWAP filter produced a $34.1\%$ win rate and lost **$-17.2R$** ($-0.10R$/trade). With Stopping Volume + AVWAP reclaim, win rate jumped to $43.3\%$ and expectancy flipped to **$+0.16R$/trade ($+4.7R$ net)** with drawdown cut from $27.9R \to 5.4R$.

---

## 3.3 Archetype 3: Volatility Contraction Breakout (`VolatilityContractionBreakoutStrategy`)
**Code:** `pa_bot/strategies.py:215-303`

### The Institutional Thesis
Before a major trend continuation leg, a stock under institutional accumulation digests prior gains in a tight sideways coil (**Volatility Contraction Pattern / VCP**). Daily trading ranges narrow (`avg_coil_range <= 0.95 * ATR`) and volume dries up as floating supply disappears. When demand steps in, price expands out of the coil on high volume above all overhead AVWAPs.

### Exact Algorithmic Rules
1. **Stacked Uptrend (`strategies.py:242`):** $C_t > \text{SMA}_{50} > \text{SMA}_{200}$.
2. **6-Bar Volatility Contraction Coil (`strategies.py:246-256`):**
   * Average range of the prior 6 bars is compressed: $\text{AvgRange}_{6} \le 0.95\text{ ATR}_{14}$.
   * Total 10-bar channel height is tight: $(\max_{10} H - \min_{6} L) \le 3.6\text{ ATR}_{14}$.
3. **Breakout Expansion & Anti-Climax Filter (`strategies.py:259-266`):**
   * Closes above the prior 10-bar resistance ceiling ($C_t > \text{coil\_high}$).
   * Bullish bar with $\text{CP}_t \ge 0.70$ and range bounded between $0.75\text{ ATR} \le \text{Range}_t \le 1.85\text{ ATR}$.
   * **Why cap at $\le 1.85\text{ ATR}$?** A breakout bar larger than $1.85\text{ ATR}$ is an exhausted climax candle—buying at its close results in immediate mean-reversion drawdown.
4. **Dry-Up $\to$ Expansion VPA & Overhead AVWAP Clearance (`strategies.py:269-279`):**
   * Coil had at least one supply dry-up day ($\min_{6} \text{RVOL} \le 0.85$).
   * Breakout bar has institutional volume expansion ($\text{RVOL}_t \ge 1.15$).
   * Closes above `avwap_swing_low`, `rolling_vwap_20`, **and** `avwap_swing_high` (Zero trapped overhead buyers).
5. **Structural Stop Placement (`strategies.py:282-286`):**
   * $\text{StopLoss} = \min(L_t, L_{t-1}) - 0.20\text{ ATR}$.
   * **Critical Lesson:** Never place a breakout stop inside the middle of the breakout candle's body. Normal post-breakout retests check the breakout level ($L_t$ or $L_{t-1}$) before resuming higher. Placing the stop structurally below $\min(L_t, L_{t-1}) - 0.20\text{ ATR}$ yields a **$53.2\%$ win rate, $+0.50R$ expectancy, and $2.11$ Profit Factor**.

---

## Mastery Gate 3 (Self-Check)

Inspect this real trade emitted by `run_lab.py`:
```text
[MSFT] 2026-09-21 -> 2026-10-06 (11d) | Entry: $501.86 | Stop: $488.45 | Exit: $534.25 | +2.41R (TARGET_HIT) | Pullback reclaim above 498.65 | AVWAP=496.59 | RVOL=1.31x
```
1. What was the initial $1R$ risk per share in dollars?
2. How did `AVWAP=496.59` and `RVOL=1.31x` confirm the entry on `2026-09-21`?
3. Why did a $2.5R$ target result in `+2.41R` realized after fills? *(Hint: check Module 4 slippage!)*
