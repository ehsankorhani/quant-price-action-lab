# Student Progress Tracker

**Student:** Ehsan  
**Current Active Module:** Module 1 — Causal Market Structure & Volatility Geometry  
**Overall Completion:** `0 / 5 Modules (0%)`

---

## Module Status Overview

| Module | Topic | Code Reference | Status | Score / Notes |
| :--- | :--- | :--- | :---: | :--- |
| **Module 1** | Causal Market Structure & Volatility Geometry | `pa_bot/data.py`, `pa_bot/indicators.py` | 🟡 Next Up | — |
| **Module 2** | Institutional VPA, RVOL & Anchored VWAP | `pa_bot/indicators.py` | ⚪ Pending | — |
| **Module 3** | The 3 Core Algorithmic Price Action Setups | `pa_bot/strategies.py` | ⚪ Pending | — |
| **Module 4** | Execution Realism & $R$-Multiple Risk Engine | `pa_bot/backtest.py` | ⚪ Pending | — |
| **Module 5** | Ablation Analysis, Stress Testing & Bot Design | `run_lab.py` | ⚪ Pending | — |

---

## Detailed Checkpoints

### Module 1: Causal Market Structure & Volatility Geometry
- [ ] **1.1 Bar Micro-Geometry & Wilder's ATR (`data.py:13-59`, `indicators.py:72-85`)**
  - Understand `typical_price`, `close_position`, `lower_wick`, and Wilder's $\text{ATR}_{14}$ smoothing.
- [ ] **1.2 Causal Pivot Confirmation (`indicators.py:98-119`)**
  - Understand why pivot index $p = i - \text{pivot\_right}$ eliminates lookahead bias and how `pivot_left=5, pivot_right=2` balances lag vs. noise.
- [ ] **1.3 Structural Regime Filter (`indicators.py:39-51`)**
  - Understand how $HH + HL$ pivots combine with $\text{SMA}_{50}/\text{SMA}_{200}$ and $\text{AVWAP}_{\text{SL}}$ to define `is_structural_uptrend`.
- [ ] **Mastery Gate 1:** Can explain what happens to pivot lag and trade count if `pivot_right` is changed from `2` to `5`.

---

### Module 2: Institutional VPA, RVOL & Anchored VWAP
- [ ] **2.1 Prefix-Sum $O(1)$ AVWAP Engine (`indicators.py:59-70`)**
  - Understand how `cum_tp_vol` and `cum_vol` compute any anchored or rolling VWAP in $O(1)$ time.
- [ ] **2.2 Dynamic Swing-Low & Swing-High AVWAPs (`indicators.py:134-143`)**
  - Understand how the anchor resets automatically when a new structural Swing Low or Swing High is confirmed.
- [ ] **2.3 RVOL & Wyckoff Effort-vs-Result (`indicators.py:130-132`, `strategies.py`)**
  - Distinguish Supply Dry-Up ($\text{RVOL} \le 0.85$), Stopping Volume ($\text{RVOL} \ge 1.10$), and Breakout Expansion ($\text{RVOL} \ge 1.15$).
- [ ] **Mastery Gate 2:** Can explain why Session VWAP fails on Daily charts and why Swing-Low AVWAP acts as institutional support.

---

### Module 3: The 3 Core Algorithmic Price Action Setups
- [ ] **3.1 Setup 1 — Trend Pullback to Structure + AVWAP (`strategies.py:35-126`)**
  - Trace entry conditions, value-zone proximity, VPA confirmation, and pullback-low stop placement.
- [ ] **3.2 Setup 2 — Liquidity Sweep / Wyckoff Spring (`strategies.py:129-212`)**
  - Trace stop-run sweep depth below support, close reclaim, Stopping Volume filter, and why Pure PA fails ($-17.2R$) without VPA ($+4.7R$).
- [ ] **3.3 Setup 3 — Volatility Contraction (VCP) Breakout (`strategies.py:215-303`)**
  - Trace 6-bar coil compression, climax bar rejection ($\le 1.85\text{ ATR}$), volume dry-up + expansion, and structural pivot stop placement ($+0.50R$/trade, PF $2.11$).
- [ ] **Mastery Gate 3:** Can read a raw trade log line from `run_lab.py` and explain every number (`Entry`, `Stop`, `AVWAP`, `RVOL`, `R-Multiple`).

---

### Module 4: Execution Realism & $R$-Multiple Risk Engine
- [ ] **4.1 Overnight Gap-Through-Stop & Slippage (`backtest.py:86-108`)**
  - Understand `STOP_GAP` vs `STOP_LOSS` vs `TARGET_HIT` and intrabar conservative ordering.
- [ ] **4.2 Breakeven Ratchet & Time Stops (`backtest.py:110-120`)**
  - Understand why stops ratchet to $+0.10R$ after $+1.5R$ unrealized gain and why stagnant trades close at `max_hold_bars`.
- [ ] **4.3 Portfolio Position Sizing & Expectancy Math (`backtest.py:165-205`)**
  - Understand fixed $1\%$ equity risk sizing, Expectancy ($E_R$), Profit Factor, and Max Drawdown in $R$.
- [ ] **Mastery Gate 4:** Can calculate exact share size and dollar risk for a given account equity, entry price, and structural stop loss.

---

### Module 5: Empirical Ablation, Stress Testing & Bot Design
- [ ] **5.1 Pure PA vs. PA + AVWAP/VPA Ablation Analysis (`run_lab.py`)**
  - Compare drawdown reduction and profit factor shifts across all 3 archetypes.
- [ ] **5.2 Multi-Ticker & Timeframe Stress Testing**
  - Compare behavior on ETFs (`SPY`, `QQQ`, `IWM`) vs. high-beta stocks (`NVDA`, `META`, `TSLA`).
- [ ] **5.3 Next-Stage Architecture Plan**
  - Define specification for `labs/02-*` (Daily Watchlist Scanner / Paper Execution Bot).
- [ ] **Mastery Gate 5:** Course graduated; ready to build and deploy `labs/02-*`.

---

## Question & Concept Log
*(Questions asked during the course and key takeaways will be logged here as we progress.)*
