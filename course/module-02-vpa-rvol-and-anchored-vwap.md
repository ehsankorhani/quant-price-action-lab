# Module 2: Institutional Volume Price Analysis (VPA), RVOL & Anchored VWAP

**Code References:**
* [`labs/01-pa-avwap-lab/pa_bot/indicators.py`](../labs/01-pa-avwap-lab/pa_bot/indicators.py) (lines `59–70`, `122–143`)
* [`labs/01-pa-avwap-lab/pa_bot/strategies.py`](../labs/01-pa-avwap-lab/pa_bot/strategies.py) (VPA & AVWAP filter blocks)

---

## 2.1 Why Session VWAP Fails on Daily Charts & How Anchored VWAP Works

### Session VWAP vs. Anchored VWAP (AVWAP)
* **Session VWAP** resets at 9:30 AM EST every trading day. On intraday charts (`1m`, `5m`, `15m`), institutional execution algorithms benchmark fills against Session VWAP. On a **Daily (`1d`)** chart, there is only 1 bar per session—so a 1-day VWAP is just that single bar's Typical Price:
  $$\text{TP}_i = \frac{H_i + L_i + C_i}{3}$$
* **Anchored VWAP ($\text{AVWAP}_{t_0 \to t}$)** starts accumulating volume and price from a **specific structural event bar $t_0$** (a confirmed Swing Low, Swing High, earnings gap, or breakout bar) up to current bar $t$:

$$\text{AVWAP}_{t_0 \to t} = \frac{\sum_{k=t_0}^{t} \text{TP}_k \cdot V_k}{\sum_{k=t_0}^{t} V_k}$$

### Why Institutions Defend the Swing-Low AVWAP
When a stock bottoms at bar $t_0$ (a confirmed Swing Low) and rallies, $\text{AVWAP}_{t_0 \to t}$ represents the **exact volume-weighted average cost basis** of every dollar transacted since that bottom:
* While $C_t > \text{AVWAP}_{t_0 \to t}$, the average participant who bought since the bottom is in profit.
* When price pulls back to touch $\text{AVWAP}_{t_0 \to t}$, institutional funds accumulating the position defend their average cost basis, while short sellers who shorted since $t_0$ reach breakeven and cover.

---

## 2.2 $O(1)$ Prefix-Sum AVWAP Engine (`indicators.py:59-70`)

Naively summing $\sum_{k=t_0}^{t} \text{TP}_k V_k$ on every bar for multiple anchors takes $O(N^2)$ time. In `indicators.py:59-70`, we precompute cumulative prefix-sum arrays once in $O(N)$ so any anchor range $[t_0, t]$ is computed in **$O(1)$ constant time**:

$$\sum_{k=t_0}^{t} \text{TP}_k V_k = \text{CumTPVol}[t + 1] - \text{CumTPVol}[t_0]$$

```python
# pa_bot/indicators.py:59-70
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
```

---

## 2.3 Dynamic Dual-Anchor Mechanics (`indicators.py:134-143`)

At every bar $i$, `compute_context()` maintains three VWAP curves simultaneously:

1. **`avwap_swing_low` (`calc_avwap(swing_low_idx, i)`):**
   * Anchored to the most recent causally confirmed Swing Low ($p = \text{swing\_low\_idx}$).
   * Used in **Trend Pullbacks** (must hold/reclaim as support) and **Liquidity Sweeps** (must reclaim after stop-run).
2. **`avwap_swing_high` (`calc_avwap(swing_high_idx, i)`):**
   * Anchored to the most recent causally confirmed Swing High ($p = \text{swing\_high\_idx}$).
   * Represents the cost basis of buyers trapped near the prior peak.
   * Used in **VCP Breakouts**: requiring `b.close >= ctx.avwap_swing_high` guarantees that trapped overhead buyers are back in the green and overhead supply is cleared.
3. **`rolling_vwap_20` (`calc_avwap(max(0, i - 19), i)`):**
   * Trailing 20-trading-day (1-month) institutional volume-weighted fair value.

---

## 2.4 Relative Volume ($\text{RVOL}$) & Wyckoff Effort-vs-Result (`indicators.py:130-132`)

Raw share volume cannot be compared across stocks or across years. We normalize volume against its trailing 20-bar Simple Moving Average:

$$\text{RVOL}_t = \frac{V_t}{\frac{1}{20}\sum_{k=t-19}^{t} V_k}$$

### The Three Institutional VPA Signatures Used in Our Code

| VPA Signature | Mathematical Condition | Institutional Meaning | Where Used |
| :--- | :--- | :--- | :--- |
| **1. Supply Dry-Up** | $\text{RVOL} \le 0.85\text{–}0.90\times$ during pullback or coil | Sellers are exhausted; institutions are holding, not distributing into the dip. | `TrendPullbackStrategy`<br>`VolatilityContractionBreakoutStrategy` |
| **2. Stopping / Absorption Volume** | $\text{RVOL} \ge 1.10\times$ on a sweep below support that closes back above support ($\text{CP}_t \ge 0.60$) | Passive institutional limit buy orders absorbed the flood of retail stop-loss market sells below support. | `LiquiditySweepStrategy` |
| **3. Expansion Volume** | $\text{RVOL} \ge 1.15\times$ on a wide-range bullish breakout bar ($\text{CP}_t \ge 0.70$) | Active institutional participation driving price through a resistance ceiling. | `TrendPullbackStrategy`<br>`VolatilityContractionBreakoutStrategy` |

---

## Mastery Gate 2 (Self-Check)

1. Why does requiring `b.close >= ctx.avwap_swing_high` on a VCP Breakout prevent buying into heavy overhead supply?
2. During a 4-day pullback toward `avwap_swing_low`, why is $\text{RVOL} = 0.65\times$ on the red pullback bars bullish, whereas $\text{RVOL} = 2.10\times$ on a wide-range red bar closing at its low ($\text{CP}_t = 0.05$) is a major red flag?
