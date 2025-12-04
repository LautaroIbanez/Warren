# Test Fixtures

This directory contains deterministic test fixtures for reproducible testing.

## Candle Fixtures

### Fixed Candle Fixture (`deterministic_candles_small`)
- **Purpose**: Small deterministic OHLCV series for edge case testing
- **Size**: 20 candles
- **Pattern**: Upward trend with small volatility
- **Hash**: Stable across runs (same data = same hash)

### Multi-Year Candle Fixture
- **Purpose**: Test CAGR and window validation
- **Size**: 800+ candles (2+ years)
- **Pattern**: Deterministic price progression
- **Use Case**: Window days validation, CAGR calculation

## Trade Fixtures

### Winning Trades Only
- **Count**: Configurable (typically 10-50)
- **Average Profit**: Configurable (typically $100-$200)
- **Use Case**: Test profit factor = infinity, positive expectancy

### Losing Trades Only
- **Count**: Configurable (typically 10-50)
- **Average Loss**: Configurable (typically -$100)
- **Use Case**: Test profit factor = 0, negative expectancy

### Mixed Trades
- **Winners**: Configurable count and profit
- **Losers**: Configurable count and loss
- **Use Case**: Test realistic profit factor, expectancy, win rate

## Expected Outputs

### Snapshot Backtest Outputs

For deterministic candle fixtures, expected metrics:
- **Total Trades**: Matches fixture count
- **Win Rate**: Calculated from winners/total
- **Profit Factor**: Calculated from gross profit/gross loss
- **Expectancy**: Average P&L per trade
- **CAGR**: Annualized return (if period >= 1 year)
- **Sharpe Ratio**: Risk-adjusted return (if >=2 return points)
- **Max Drawdown**: Maximum peak-to-trough decline

### Hash Consistency

- Same candle data → Same hash
- Same candles_hash + timestamp → Same backtest_hash
- Hash mismatch → Cache invalidation

## Using Fixtures

```python
def test_my_feature(backtest_engine, deterministic_candles_small, winning_trades):
    # Use fixtures from conftest.py
    result = backtest_engine.run("BTCUSDT", "1d", deterministic_candles_small)
    metrics = backtest_engine._calculate_metrics(winning_trades, equity_curve)
```

## Maintaining Fixtures

When updating fixtures:
1. Ensure deterministic behavior (same input = same output)
2. Update expected snapshot values if fixture changes
3. Verify hash stability across runs
4. Document any changes in this README

