# Module 1: Causal Market Structure & Volatility Geometry

**Code References:**
* [`labs/01-pa-avwap-lab/pa_bot/data.py`](../labs/01-pa-avwap-lab/pa_bot/data.py) (lines `13–59`)
* [`labs/01-pa-avwap-lab/pa_bot/indicators.py`](../labs/01-pa-avwap-lab/pa_bot/indicators.py) (lines `39–119`)

---

## 1.1 Dimensionless Bar Micro-Geometry & Wilder's $\text{ATR}_{14}$

### Why Fixed Percentages Fail
In algorithmic price action, hardcoding percentages (e.g., *"stop loss 2% below entry"* or *"candle body > 1%"*) breaks immediately across tickers and volatility regimes:
* On `SPY`, a $1.5\%$ daily range is a high-conviction institutional expansion bar.
* On `NVDA`, a $1.5\%$ daily range is a quiet inside bar.

To make strategy rules invariant across tickers and timeframes, every spatial measurement—candle body, wick length, pullback proximity, sweep depth, and stop buffer—must be normalized by **Wilder's 14-bar Average True Range ($\text{ATR}_{14}$)** or by the bar's own total range ($H_t - L_t$).

---

### True Range ($\text{TR}_t$) & Wilder's Smoothing (`indicators.py:72-85`)

A single bar's `high - low` misses overnight gaps. **True Range ($\text{TR}_t$)** measures the full vertical distance traveled from yesterday's close $C_{t-1}$:

$$\text{TR}_t = \max\big(H_t - L_t,\; |H_t - C_{t-1}|,\; |L_t - C_{t-1}|\big)$$

In `indicators.py:72-85`, we smooth $\text{TR}_t$ using **Wilder's recurrence** ($\alpha = \frac{1}{14}$):

$$\text{ATR}_t = \frac{13 \cdot \text{ATR}_{t-1} + \text{TR}_t}{14}$$

```python
# pa_bot/indicators.py:74-85
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
```

> **Engineering Insight — Why Wilder's $\alpha = \frac{1}{14}$ instead of standard EMA $\alpha = \frac{2}{15}$?**  
> Standard EMA weights recent quiet bars almost twice as heavily ($\frac{2}{15} \approx 13.3\%$ vs $\frac{1}{14} \approx 7.1\%$). After a major volatility shock, Wilder's ATR decays more slowly, preventing your bot from tightening structural stops too aggressively while post-shock aftershocks are still occurring.

---

### Replacing Candlestick Names with $\text{ClosePosition}_t$ (`data.py:24-59`)

Retail price action memorizes dozens of subjective candlestick labels (*hammer, shooting star, pin bar, marubozu*). Algorithmic price action replaces all single-bar patterns with two continuous dimensionless ratios in `Bar` (`data.py:24-59`):

1. **Close Position ($\text{CP}_t$):** Where the close sits inside the bar's high-low auction range:
   $$\text{CP}_t = \frac{C_t - L_t}{H_t - L_t} \in [0.0, 1.0]$$
   * $\text{CP}_t \ge 0.65$: Buyers controlled the auction into the close (closing in the top $35\%$ of the bar's range), regardless of whether the bar opened high or gapped down at the open.
   * $\text{CP}_t \le 0.30$: Sellers dominated into the close.

2. **Lower Rejection Tail Ratio (`lower_wick / range`):**
   $$\text{TailRatio}_t = \frac{\min(O_t, C_t) - L_t}{H_t - L_t} \in [0.0, 1.0]$$
   * When $\text{TailRatio}_t \ge 0.45$ and $\text{CP}_t \ge 0.60$ at a structural support level, intrabar sell orders were absorbed by limit buyers.

---

## 1.2 Lookahead-Free Asymmetric Fractal Pivots (`indicators.py:98-119`)

### The #1 Retail Backtesting Bug: Centered Window Lookahead
When coding Swing Highs ($SH$) and Swing Lows ($SL$), a common mistake is checking whether bar $i$ is the minimum of `[i - 5 ... i + 5]` while evaluating trade signals on bar $i$.
* **Why that cheats:** At bar $i$, bars `i + 1 ... i + 5` have not happened yet. Knowing that bar $i$ is lower than the next 5 bars guarantees that price rises over the next 5 bars!

### Causal Asymmetric Confirmation (`pivot_left = 5`, `pivot_right = 2`)
At the close of current bar $i$, the most recent bar that has `pivot_right = 2` completed bars to its right is candidate bar $p = i - 2$:

$$p = i - R, \quad \text{where } R = \text{pivot\_right} = 2,\; L = \text{pivot\_left} = 5$$

Candidate bar $p$ is confirmed as a **structural Swing Low** at the close of bar $i$ if and only if:

$$L_p \le \min_{k \in [p - L,\; p - 1]} L_k \quad \land \quad L_p < \min_{k \in [p + 1,\; i]} L_k$$

```python
# pa_bot/indicators.py:99-119
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
```

```text
  [ p-5   p-4   p-3   p-2   p-1 ]      [ p ]       [ p+1    i ]
  |--------- L = 5 bars --------|   Candidate SL   |-- R = 2 --|
   Must all have Low >= Low[p]       Anchor idx=p   Must have Low > Low[p]
                                                   (Confirmed at Bar i close!)
```

### Why Asymmetric ($L = 5, R = 2$) Beats Symmetric ($L = 5, R = 5$)
| Parameter | Role | Tradeoff |
| :--- | :--- | :--- |
| **`pivot_left = 5`** | **Structural Significance** | Requires the low at $p$ to undercut a full 5-day trading week of prior action, filtering out minor 1–2 day noise. |
| **`pivot_right = 2`** | **Confirmation Speed (Lag)** | Locks in the pivot after just 2 higher daily lows. If $R = 5$, you wait 5 full days after the bottom to confirm it—by which time the pullback/rebound entry is already gone. |

---

## 1.3 The Structural Regime State Machine (`indicators.py:39-51`)

In `BarContext.is_structural_uptrend`, we classify whether long trend setups are permitted at bar $i$:

```python
# pa_bot/indicators.py:39-51
@property
def is_structural_uptrend(self) -> bool:
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
```

### Why `ma_trend AND (hh_hl OR close > avwap_swing_low)`?
1. **Macro Institutional Trend (`ma_trend`):** Price must be above its 50-day SMA, and the 50-day SMA must be above (or within $1\%$ of) the 200-day SMA. This keeps Trend Pullback strategies out of secular bear markets (like 2022).
2. **Pivot Structure OR Cost-Basis Control:**
   * In a classic stair-step trend, confirmed pivots form Higher Highs ($SH_1 > SH_0$) and Higher Lows ($SL_1 > SL_0$).
   * However, right after a liquidity sweep (where a pullback briefly undercuts $SL_0$ by a few cents to run stops before surging higher), `swing_low_price > prev_swing_low_price` temporarily evaluates to `False`.
   * Including `or self.bar.close > self.avwap_swing_low` recognizes that as long as price is above the 50/200 SMA stack **and** buyers from the active Swing Low are in net profit (`close > avwap_swing_low`), the uptrend is structurally intact.

---

## Mastery Gate 1 (Self-Check)

1. Suppose you change `pivot_right` in `compute_context()` from `2` to `6` (`pivot_left = 5, pivot_right = 6`). What happens to **when** the bot discovers a new Swing Low (`swing_low_idx`)?
2. How does that delay affect `avwap_swing_low` during a 3-day pullback right after a major bottom forms?
