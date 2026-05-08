# BMV Backtesting Statistical Report

Generated at: 2026-04-22 17:18:25

## Executive Summary
- **Total Scenarios Analyzed**: 17
- **Statistical Significance (P-Value)**: 0.0995 (Not Significant)
- **Aggregate T-Statistic**: -1.6479
- **Estimated Risk of Ruin (50% Drawdown)**: 100.00%

## Regime Performance
| regime      |         pnl |    sharpe |    max_dd |   profit_factor |
|:------------|------------:|----------:|----------:|----------------:|
| Adversarial |    -28.3519 |  -65.3959 | 0.0843017 |       0.0511332 |
| Bear        | -13320.7    |  -28.3786 | 0.244225  |       0.144521  |
| Bull        | -17743      | -152.252  | 0.305737  |       4.84159   |
| Neutral     | -31064.7    | -198.458  | 0.34089   |      19.0587    |
| Sideways    | -10897.4    |  -12.1416 | 0.184741  |     100         |

## Monte Carlo Robustness
### Scenario: Adversarial_RugPull.json
- Mean Sharpe: 153.56
- VaR (95%): 0.00
- Iterations: 50

