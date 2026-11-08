# Quantified Price Action & AVWAP Trading Lab (`quant-price-action-lab`)

A mid-to-advanced hands-on course and strategy laboratory for translating discretionary **Price Action**, **Volume Price Analysis (VPA)**, and **Anchored VWAP (AVWAP)** into deterministic, backtested Python trading systems.

---

## Repository Structure

```text
quant-price-action-lab/
├── README.md                  # Project overview & quickstart
├── CURRICULUM.md              # Mid-to-advanced 5-module fast-track curriculum
├── PROGRESS.md                # Interactive student progress tracker & mastery gates
└── labs/                      # Code laboratories (current + future modules)
    └── 01-pa-avwap-lab/       # Lab 01: Core Price Action + AVWAP/VPA Engine
        ├── run_lab.py         # CLI strategy comparison & ablation runner
        └── pa_bot/
            ├── data.py        # Yahoo Finance v8 OHLCV fetcher, cache & bar geometry
            ├── indicators.py  # Causal fractal pivots, ATR(14), RVOL & O(1) AVWAP
            ├── strategies.py  # 3 Core Setups (Trend Pullback, Liquidity Sweep, VCP)
            └── backtest.py    # Event-driven swing backtester with gap/slippage realism
```

---

## Quickstart (Zero External Dependencies)

Requires Python 3.10+ (uses standard library only):

```bash
python3 labs/01-pa-avwap-lab/run_lab.py
```

Run on custom tickers or lookback windows:

```bash
python3 labs/01-pa-avwap-lab/run_lab.py --symbols SPY QQQ NVDA META --period 5y
```

---

## Course Workflow

1. Review the syllabus in [`CURRICULUM.md`](./CURRICULUM.md).
2. Track active lessons, code line references, and mastery checkpoints in [`PROGRESS.md`](./PROGRESS.md).
3. Run and inspect laboratories inside [`labs/`](./labs/).
