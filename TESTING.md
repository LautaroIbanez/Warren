# Warren Testing Guide

This document provides comprehensive information about the Warren test suite, including how to run tests, test coverage, and CI/CD integration.

## Test Structure

### Backend Tests (`tests/`)

#### Policy & Blocking Tests
- **`test_policy_violations.py`**: Unit tests for individual policy violation checks
- **`test_comprehensive_policy.py`**: Comprehensive integration tests covering all violation scenarios:
  - Insufficient trades (<30)
  - Negative/zero return
  - Profit factor below threshold
  - Excessive drawdown (>50%)
  - Stale cache
  - Insufficient window (<730 days)
  - Multiple violations

#### Metric Calculation Tests
- **`test_backtest_metrics.py`**: Unit tests for metric calculations (profit factor, win rate, expectancy, Sharpe ratio, drawdown)
- **`test_edge_cases.py`**: Edge case tests (no trades, single winner/loser, breakeven)

#### Reliability Tests
- **`test_reliability.py`**: Tests for reliability logic and threshold validation
- **`test_risk_repository_reliability.py`**: Tests for risk repository reliability calculation with window_days

#### Integration Tests
- **`test_recommendation_blocking.py`**: Tests for recommendation endpoint blocking logic
- **`test_refresh_integration.py`**: Integration tests for refresh endpoint
- **`test_stale_cache_integration.py`**: Integration tests for stale cache scenarios
- **`test_refresh_snapshots.py`**: Snapshot/regression tests for refresh pipeline consistency

#### Hash & Data Integrity Tests
- **`test_deterministic_hashing.py`**: Tests for deterministic hashing (existing)
- **`test_hash_determinism.py`**: Comprehensive deterministic hash tests for identical candle data

#### Synthetic Trade Set Tests
- **`test_synthetic_trade_sets.py`**: Unit tests for metrics with synthetic trade sets:
  - Wins only (profit factor = infinity)
  - Losses only (profit factor = 0)
  - Mixed trades (various profit factors)
  - Expectancy, Sharpe, CAGR, max drawdown calculations

#### Snapshot & Regression Tests
- **`test_snapshot_backtests.py`**: Snapshot/regression tests for backtest outputs:
  - Deterministic candle fixture produces stable hash
  - Backtest output reproducibility
  - Hash consistency between candles and backtest
  - JSON serialization consistency
  - Hash mismatch cache invalidation

#### End-to-End Integration Tests
- **`test_end_to_end_refresh_flow.py`**: Complete refresh → backtest → risk → recommendation flow:
  - Fixed candle fixture flow
  - Blocks when thresholds violated
  - Allows when thresholds met
  - Cache behavior (stale/inconsistent hashes)

### Frontend Tests (`frontend/`)

#### Unit Tests
- **`src/components/__tests__/RiskPanel.test.tsx`**: Unit tests for RiskPanel component
- **`src/pages/__tests__/Dashboard.test.tsx`**: Unit tests for Dashboard component
- **`src/pages/__tests__/Dashboard.snapshot.test.tsx`**: Snapshot tests for Dashboard rendering
- **`src/pages/__tests__/Dashboard.dom.test.tsx`**: DOM structure tests for blocked/allowed banners and hash display
- **`src/utils/__tests__/formatting.test.ts`**: Formatting tests for percent/currency/number localization

#### E2E Tests
- **`e2e/dashboard.spec.ts`**: Playwright E2E tests for Dashboard UI

## Running Tests

### Backend Tests

#### Prerequisites
```bash
pip install -r requirements.txt
```

#### Run All Tests
```bash
pytest tests/ -v
```

#### Run Specific Test File
```bash
pytest tests/test_comprehensive_policy.py -v
```

#### Run Tests Headlessly (for CI)
```bash
pytest tests/ -v --tb=short
```

#### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Frontend Tests

#### Prerequisites
```bash
cd frontend
npm install
```

#### Run Unit Tests
```bash
npm test
```

#### Run Unit Tests Headlessly (for CI)
```bash
npm test -- --run
```

#### Run E2E Tests
```bash
npm run test:e2e
```

#### Run E2E Tests Headlessly
```bash
npx playwright test
```

## Test Coverage

### Policy Violations

All policy violation scenarios are tested:

1. **Insufficient Trades**: `< MIN_TRADES_FOR_RELIABILITY (30)`
2. **Negative/Zero Return**: `<= MIN_TOTAL_RETURN_PCT (0.0%)`
3. **Low Profit Factor**: `< MIN_PROFIT_FACTOR (1.0)`
4. **Excessive Drawdown**: `> MAX_DRAWDOWN_PCT (50%)`
5. **Stale Cache**: Data older than `STALE_CANDLE_HOURS (24h)`
6. **Insufficient Window**: `< MIN_DATA_WINDOW_DAYS (730 days)`

### Hash Determinism

Tests verify:
- Identical candle data produces identical hash
- Hash is independent of DataFrame row order (after sorting)
- Different data produces different hash
- Hash changes with timestamp changes
- Backtest hash is deterministic for same inputs

### Frontend Rendering

Tests verify:
- Blocked banner renders with red styling
- Allowed banner renders with green styling
- Hash values display correctly (truncated)
- Violation lists display all reasons
- Currency and percentage formatting

## CI/CD Integration

### GitHub Actions

The test suite runs automatically via `.github/workflows/test.yml` on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

### CI Workflow

1. **Backend Tests**: Runs pytest with coverage reporting
2. **Frontend Unit Tests**: Runs Vitest in headless mode
3. **Frontend E2E Tests**: Runs Playwright tests

### Local CI Simulation

To simulate CI locally:

```bash
# Backend
pytest tests/ -v --tb=short

# Frontend
cd frontend
npm test -- --run
npx playwright test
```

## Test Fixtures

### Backend Fixtures (`tests/conftest.py`)

- `temp_data_dir`: Temporary directory for test data
- `sample_candles`: Generated candle data
- `deterministic_candles_small`: Small deterministic OHLCV series
- `deterministic_candles_no_trend`: Deterministic candles with no trend
- `deterministic_candles_downtrend`: Deterministic candles with downward trend
- `winning_trades`: List of profitable trades
- `losing_trades`: List of losing trades
- `breakeven_trades`: List of zero-PnL trades
- `single_winning_trade`: Single winning trade
- `single_losing_trade`: Single losing trade
- `mixed_trades`: Combination of all trade types
- `equity_curve`: Sample equity curve data
- `backtest_engine`: BacktestEngine instance

### Frontend Mocks (`frontend/src/test/mocks/api.ts`)

- `mockBlockedRecommendation`: Mock API response for blocked signal
- `mockStaleRecommendation`: Mock API response for stale signal
- `mockGoodRecommendation`: Mock API response for valid signal
- `mockRiskMetricsUnreliable`: Mock risk metrics with unreliable data
- `mockRiskMetricsReliable`: Mock risk metrics with reliable data
- `mockRefreshResponse`: Mock refresh endpoint response

## Writing New Tests

### Backend Test Guidelines

1. Follow naming convention: `test_*.py` for files, `test_*` for functions
2. Use fixtures from `conftest.py` when possible
3. Mock external dependencies (API calls, file I/O)
4. Test both success and failure cases
5. Include edge cases (empty data, zero values, nulls)

### Frontend Test Guidelines

1. Use Vitest for unit tests
2. Use Playwright for E2E tests
3. Mock API responses using MSW or manual mocks
4. Test user interactions and visual rendering
5. Use snapshot tests for UI regression detection

## Test Maintenance

### Updating Snapshots

If UI changes intentionally, update snapshots:
```bash
cd frontend
npm test -- --run -u
```

### Debugging Tests

#### Backend
```bash
pytest tests/test_comprehensive_policy.py::TestComprehensivePolicyViolations::test_insufficient_trades_blocks_signal -v -s
```

#### Frontend
```bash
cd frontend
npm test -- --run --reporter=verbose
```

## Coverage Goals

- **Backend**: >80% code coverage
- **Frontend**: >70% code coverage
- **Critical Paths**: 100% coverage (policy, metrics, blocking logic)

## Continuous Integration

Tests run automatically on:
- Every push to main/develop
- Every pull request
- Before deployment

All tests must pass before code can be merged.

