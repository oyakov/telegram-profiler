# Solana DEX BMV - Comprehensive Backtest Analysis Report

**Generated:** 2026-04-30 19:52:05
**Total Scenarios:** 14
**Successful Runs:** 14

---

## Performance Rankings

### Top 10 by Total PnL (Realized + Unrealized)

| Rank | Scenario | Total PnL | Realized PnL | Win Rate | Sharpe | Max DD | Trades |
|------|----------|-----------|--------------|----------|--------|--------|--------|
| 1 | flash_crash | 422.8197 | 422.8197 | 2.7% | 2.65 | 0.00% | 13 |
| 2 | bear_crash | 306.7522 | 306.7522 | 16.7% | 7.10 | 0.00% | 4 |
| 3 | real_sol_365d | 112.5034 | 112.5034 | 25.0% | 9.16 | 0.00% | 7 |
| 4 | high_volatility | 94.6902 | 94.6902 | 50.0% | 15.87 | 0.00% | 6 |
| 5 | bull_run | 10.1447 | 10.1447 | 5.3% | 3.73 | 0.00% | 1 |
| 6 | pump_and_dump | 4.8449 | 4.8449 | 25.0% | 9.16 | 0.00% | 1 |
| 7 | Adversarial_AggressiveMoon | 0.0000 | 0.0000 | 0.0% | 0.00 | 0.02% | 0 |
| 8 | Adversarial_InitialDump | 0.0000 | 0.0000 | 0.0% | 0.00 | 0.02% | 0 |
| 9 | Adversarial_RugPull | 0.0000 | 0.0000 | 0.0% | 0.00 | 0.02% | 0 |
| 10 | Adversarial_SlowMoon | 0.0000 | 0.0000 | 0.0% | 0.00 | 0.02% | 0 |

### Top 10 by Risk-Adjusted Return (Sharpe Ratio)

| Rank | Scenario | Sharpe | Total PnL | Win Rate | Sortino | Max DD |
|------|----------|--------|-----------|----------|---------|--------|
| 1 | high_volatility | 15.874 | 94.6902 | 50.0% | 0.00 | 0.00% |
| 2 | real_sol_365d | 9.165 | 112.5034 | 25.0% | 0.00 | 0.00% |
| 3 | pump_and_dump | 9.158 | 4.8449 | 25.0% | 0.00 | 0.00% |
| 4 | bear_crash | 7.099 | 306.7522 | 16.7% | 0.00 | 0.00% |
| 5 | bull_run | 3.735 | 10.1447 | 5.3% | 0.00 | 0.00% |
| 6 | flash_crash | 2.646 | 422.8197 | 2.7% | 0.00 | 0.00% |
| 7 | Adversarial_AggressiveMoon | 0.000 | 0.0000 | 0.0% | 0.00 | 0.02% |
| 8 | Adversarial_InitialDump | 0.000 | 0.0000 | 0.0% | 0.00 | 0.02% |
| 9 | Adversarial_RugPull | 0.000 | 0.0000 | 0.0% | 0.00 | 0.02% |
| 10 | Adversarial_SlowMoon | 0.000 | 0.0000 | 0.0% | 0.00 | 0.02% |

### Top 10 by Win Rate

| Rank | Scenario | Win Rate | Trade Count | Total PnL | Sharpe | Profit Factor |
|------|----------|----------|-------------|-----------|--------|---------------|
| 1 | high_volatility | 50.0% | 6 | 94.6902 | 15.87 | 94689.18 |
| 2 | pump_and_dump | 25.0% | 1 | 4.8449 | 9.16 | 1614.62 |
| 3 | real_sol_365d | 25.0% | 7 | 112.5034 | 9.16 | 37500.79 |
| 4 | bear_crash | 16.7% | 4 | 306.7522 | 7.10 | 61350.23 |
| 5 | launch_attack | 8.6% | 3268 | -294.9230 | -11.09 | 0.01 |
| 6 | bull_run | 5.3% | 1 | 10.1447 | 3.73 | 563.54 |
| 7 | flash_crash | 2.7% | 13 | 422.8197 | 2.65 | 11744.96 |
| 8 | Adversarial_AggressiveMoon | 0.0% | 0 | 0.0000 | 0.00 | 0.00 |
| 9 | Adversarial_InitialDump | 0.0% | 0 | 0.0000 | 0.00 | 0.00 |
| 10 | Adversarial_RugPull | 0.0% | 0 | 0.0000 | 0.00 | 0.00 |

---

## Aggregate Statistics

### Portfolio Metrics

**Total PnL (SOL)**
- Mean: 46.9166
- Median: 0.0000
- Std Dev: 164.2667
- Min: -294.9230
- Max: 422.8197

**Sharpe Ratio**
- Mean: 2.61
- Median: 0.00
- Std Dev: 6.32
- Min: -11.09
- Max: 15.87

**Win Rate**
- Mean: 9.5%
- Median: 1.4%
- Min: 0.0%
- Max: 50.0%

**Trade Count**
- Mean: 236
- Median: 0
- Total: 3300

**Max Drawdown (%)**
- Mean: 2.12%
- Median: 0.02%
- Min: 0.00%
- Max: 29.50%

**Profit Factor**
- Mean: 29637.62
- Median: 11744.96
- Min: 0.01
- Max: 94689.18

---

## Scenario Category Analysis

### Adversarial (4 scenarios)

**Avg PnL:** 0.0000 SOL  **Avg Sharpe:** 0.00  **Avg Win Rate:** 0.0%

### Bear (1 scenarios)

**Avg PnL:** 306.7522 SOL  **Avg Sharpe:** 7.10  **Avg Win Rate:** 16.7%

### Bull (1 scenarios)

**Avg PnL:** 10.1447 SOL  **Avg Sharpe:** 3.73  **Avg Win Rate:** 5.3%

### Choppy/Sideways (2 scenarios)

**Avg PnL:** 0.0000 SOL  **Avg Sharpe:** 0.00  **Avg Win Rate:** 0.0%

### Flash Crash (1 scenarios)

**Avg PnL:** 422.8197 SOL  **Avg Sharpe:** 2.65  **Avg Win Rate:** 2.7%

### Launch Attack (1 scenarios)

**Avg PnL:** -294.9230 SOL  **Avg Sharpe:** -11.09  **Avg Win Rate:** 8.6%

### Other (2 scenarios)

**Avg PnL:** 47.3451 SOL  **Avg Sharpe:** 7.94  **Avg Win Rate:** 25.0%

### Pump & Dump (1 scenarios)

**Avg PnL:** 4.8449 SOL  **Avg Sharpe:** 9.16  **Avg Win Rate:** 25.0%

### Real Data (1 scenarios)

**Avg PnL:** 112.5034 SOL  **Avg Sharpe:** 9.16  **Avg Win Rate:** 25.0%

---

## Complete Results Table

| Scenario | Total PnL | Trades | Win Rate | Sharpe | Sortino | Max DD | Profit Factor |
|----------|-----------|--------|----------|--------|---------|--------|---------------|
| flash_crash | 422.8197 | 13 | 2.7% | 2.65 | 0.00 | 0.00% | 11744.96 |
| bear_crash | 306.7522 | 4 | 16.7% | 7.10 | 0.00 | 0.00% | 61350.23 |
| real_sol_365d | 112.5034 | 7 | 25.0% | 9.16 | 0.00 | 0.00% | 37500.79 |
| high_volatility | 94.6902 | 6 | 50.0% | 15.87 | 0.00 | 0.00% | 94689.18 |
| bull_run | 10.1447 | 1 | 5.3% | 3.73 | 0.00 | 0.00% | 563.54 |
| pump_and_dump | 4.8449 | 1 | 25.0% | 9.16 | 0.00 | 0.00% | 1614.62 |
| Adversarial_AggressiveMoon | 0.0000 | 0 | 0.0% | 0.00 | 0.00 | 0.02% | 0.00 |
| Adversarial_InitialDump | 0.0000 | 0 | 0.0% | 0.00 | 0.00 | 0.02% | 0.00 |
| Adversarial_RugPull | 0.0000 | 0 | 0.0% | 0.00 | 0.00 | 0.02% | 0.00 |
| Adversarial_SlowMoon | 0.0000 | 0 | 0.0% | 0.00 | 0.00 | 0.02% | 0.00 |
| choppy_sideways | 0.0000 | 0 | 0.0% | 0.00 | 0.00 | 0.02% | 0.00 |
| low_liquidity | 0.0000 | 0 | 0.0% | 0.00 | 0.00 | 0.01% | 0.00 |
| sideways_chop | 0.0000 | 0 | 0.0% | 0.00 | 0.00 | 0.03% | 0.00 |
| launch_attack | -294.9230 | 3268 | 8.6% | -11.09 | -10.94 | 29.50% | 0.01 |

---

## Key Insights

**Best Absolute Return:** flash_crash (422.8197 SOL)

**Best Risk-Adjusted Return:** high_volatility (Sharpe: 15.87)

**Best Win Rate:** high_volatility (50.0%)

**Profitability:** 6/14 scenarios profitable (42.9%)

OK - Average Sharpe: 2.61 (good risk-adjusted returns)

**Max Drawdown Range:** 0.00% to 29.50%
