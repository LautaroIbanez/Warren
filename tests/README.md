# Warren Test Suite

This directory contains automated tests for the Warren trading system.

## Test Structure

### Backend Tests

- `conftest.py`: Shared pytest fixtures and configuration
- `test_backtest_metrics.py`: Unit tests for metric calculations (profit factor, win rate, expectancy, Sharpe ratio, drawdown)
- `test_reliability.py`: Tests for reliability logic and threshold validation
- `test_recommendation_blocking.py`: Tests for recommendation endpoint blocking logic
- `test_refresh_integration.py`: Integration tests for refresh endpoint
- `test_edge_cases.py`: Edge case tests with deterministic candle fixtures (no trades, single winner/loser, breakeven)
- `test_stale_cache_integration.py`: Integration tests for stale cache scenarios
- `test_refresh_snapshots.py`: Snapshot/regression tests for refresh pipeline consistency
- `test_comprehensive_policy.py`: Comprehensive policy violation integration tests
- `test_hash_determinism.py`: Deterministic hash tests for identical candle data
- `test_policy_violations.py`: Unit tests for individual policy violation checks

### Frontend Tests

- `src/test/mocks/api.ts`: Mock API responses for testing
- `src/components/__tests__/RiskPanel.test.tsx`: Unit tests for RiskPanel component
- `src/pages/__tests__/Dashboard.test.tsx`: Unit tests for Dashboard component
- `src/pages/__tests__/Dashboard.snapshot.test.tsx`: Snapshot tests for Dashboard rendering
- `src/pages/__tests__/Dashboard.dom.test.tsx`: DOM structure tests for Dashboard
- `e2e/dashboard.spec.ts`: Playwright E2E tests for Dashboard UI

## Running Tests

### Backend Tests

#### Install Dependencies

```bash
pip install -r requirements.txt
```

#### Run All Tests

```bash
pytest
```

#### Run Specific Test File

```bash
pytest tests/test_backtest_metrics.py
```

#### Run with Verbose Output

```bash
pytest -v
```

#### Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

### Frontend Tests

#### Install Dependencies

```bash
cd frontend
npm install
```

#### Run Unit Tests

```bash
npm test
```

#### Run Unit Tests in Watch Mode

```bash
npm test -- --watch
```

#### Run Unit Tests Headlessly (for CI)

```bash
npm test -- --run
```

#### Run Unit Tests with UI

```bash
npm run test:ui
```

#### Run E2E Tests

```bash
npm run test:e2e
```

#### Run E2E Tests Headlessly

```bash
npx playwright test
```

### CI/CD

The test suite runs automatically on push/PR via GitHub Actions (`.github/workflows/test.yml`).

To run tests locally in CI mode:
```bash
# Backend
pytest tests/ -v --tb=short

# Frontend
cd frontend
npm test -- --run
npx playwright test
```

## Test Coverage

### Unit Tests

- **Metric Calculations**: Tests verify correct calculation of:
  - Profit factor: `sum(positive pnl) / abs(sum(negative pnl))`
  - Win rate: Only counts winners, breakeven trades are neutral
  - Expectancy: Average P&L per trade (includes breakeven as zero)
  - Sharpe ratio: Standard formula without arbitrary ×100 scaling
  - Max drawdown: Calculated from equity curve peaks

- **Reliability Logic**: Tests verify `is_reliable` flag:
  - Toggles correctly based on trade count threshold
  - Toggles based on profit factor threshold
  - Toggles based on total return threshold
  - Toggles based on max drawdown threshold
  - Includes all failing thresholds in reason string

### Integration Tests

- **Recommendation Endpoint**: Tests verify:
  - Blocks signals when metrics are poor
  - Passes signals when metrics are good
  - Blocks on stale cache
  - Returns proper error messages

- **Refresh Endpoint**: Tests verify:
  - Returns all snapshots (recommendation, backtest, candles, risk)
  - Snapshots have aligned hashes and timestamps
  - Handles partial failures gracefully
  - Fails appropriately when all snapshots fail

## Fixtures

The test suite includes reusable fixtures:

### Backend Fixtures

- `sample_candles`: Generated candle data for testing
- `deterministic_candles_small`: Small deterministic OHLCV series (20 candles)
- `deterministic_candles_no_trend`: Deterministic candles with no clear trend
- `deterministic_candles_downtrend`: Deterministic candles with downward trend
- `winning_trades`: List of profitable trades
- `losing_trades`: List of losing trades
- `breakeven_trades`: List of zero-PnL trades
- `single_winning_trade`: Single winning trade fixture
- `single_losing_trade`: Single losing trade fixture
- `mixed_trades`: Combination of all trade types
- `equity_curve`: Sample equity curve data
- `backtest_engine`: BacktestEngine instance for testing
- `temp_data_dir`: Temporary directory for test data

### Frontend Mocks

- `mockBlockedRecommendation`: Mock API response for blocked signal
- `mockStaleRecommendation`: Mock API response for stale signal
- `mockGoodRecommendation`: Mock API response for valid signal
- `mockRiskMetricsUnreliable`: Mock risk metrics with unreliable data
- `mockRiskMetricsReliable`: Mock risk metrics with reliable data
- `mockRefreshResponse`: Mock refresh endpoint response

## Writing New Tests

When adding new tests:

1. Follow the naming convention: `test_*.py` for files, `test_*` for functions
2. Use fixtures from `conftest.py` when possible
3. Mock external dependencies (API calls, file I/O)
4. Test both success and failure cases
5. Include edge cases (empty data, zero values, etc.)

## Continuous Integration

These tests should be run in CI/CD pipelines before deploying changes to ensure:
- Metric calculations remain correct
- Blocking logic works as expected
- Endpoints return proper responses
- Data integrity is maintained

