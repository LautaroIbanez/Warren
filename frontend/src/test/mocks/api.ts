/** Mock API responses for testing. */

export const mockBlockedRecommendation = {
  signal: "HOLD",
  confidence: 0.0,
  entry_price: null,
  stop_loss: null,
  take_profit: null,
  rationale: "Señal bloqueada: Insuficientes trades: 25 < 30 mínimo requerido",
  is_blocked: true,
  block_reason: "Insuficientes trades: 25 < 30 mínimo requerido",
  block_reasons: [
    "Insuficientes trades: 25 < 30 mínimo requerido",
    "Profit factor insuficiente: 0.85 < 1.0 mínimo requerido"
  ],
  candles_hash: "test_hash_123",
  as_of: "2022-01-01T12:00:00"
};

export const mockStaleRecommendation = {
  signal: "BUY",
  confidence: 0.8,
  entry_price: 40000.0,
  stop_loss: 38000.0,
  take_profit: 42000.0,
  rationale: "Strong buy signal",
  is_stale_signal: true,
  stale_reason: "Last candle is 25.5 hours old",
  candles_hash: "test_hash_123",
  as_of: "2022-01-01T12:00:00"
};

export const mockGoodRecommendation = {
  signal: "BUY",
  confidence: 0.85,
  entry_price: 40000.0,
  stop_loss: 38000.0,
  take_profit: 42000.0,
  rationale: "Strong buy signal based on technical analysis",
  candles_hash: "test_hash_123",
  as_of: "2022-01-01T12:00:00"
};

export const mockRiskMetricsUnreliable = {
  metrics: {
    total_trades: 25,
    win_rate: 55.0,
    profit_factor: 0.85,
    expectancy: -10.5,
    cagr: 5.2,
    sharpe_ratio: 0.8,
    max_drawdown: 15.5,
    total_return: 8.5,
    is_reliable: false,
    reason: "Only 25 trades (need 30+)"
  },
  validation: {
    trade_count: 25,
    window_days: 100,
    min_trades_required: 30,
    min_window_days: 90,
    is_reliable: false
  },
  status: "degraded",
  reason: "Only 25 trades (need 30+)"
};

export const mockRiskMetricsReliable = {
  metrics: {
    total_trades: 35,
    win_rate: 60.0,
    profit_factor: 1.5,
    expectancy: 25.5,
    cagr: 12.5,
    sharpe_ratio: 1.2,
    max_drawdown: 20.0,
    total_return: 15.5,
    is_reliable: true,
    reason: null
  },
  validation: {
    trade_count: 35,
    window_days: 100,
    min_trades_required: 30,
    min_window_days: 90,
    is_reliable: true
  },
  status: "ok",
  reason: null
};

export const mockRefreshResponse = {
  refresh: {
    success: true,
    symbol: "BTCUSDT",
    interval: "1d",
    rows_added: 10
  },
  snapshots: {
    recommendation: mockGoodRecommendation,
    backtest: {
      trades: [],
      equity_curve: [],
      metrics: { total_trades: 35 }
    },
    candles: {
      candles: [],
      metadata: {
        candles_hash: "test_hash_123",
        as_of: "2022-01-01T12:00:00"
      }
    },
    risk: mockRiskMetricsReliable
  },
  errors: null
};

