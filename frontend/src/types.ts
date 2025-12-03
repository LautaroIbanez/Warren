/** Tipos TypeScript para la aplicación Warren. */

export type Signal = "BUY" | "SELL" | "HOLD";

export interface Recommendation {
  signal: Signal;
  confidence: number;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  rationale: string;
  as_of?: string;
  data_freshness?: {
    as_of: string;
    is_stale: boolean;
    hours_old: number;
    reason: string;
  };
}

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Trade {
  entry_time: string;
  exit_time: string | null;
  entry_price: number;
  exit_price: number | null;
  stop_loss: number;
  take_profit: number;
  signal: Signal;
  confidence: number;
  pnl: number | null;
  pnl_pct: number | null;
  exit_reason: string | null;
}

export interface BacktestMetrics {
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  expectancy: number;
  cagr: number;
  sharpe_ratio: number;
  max_drawdown: number;
  total_return: number;
  is_reliable: boolean;
  reason: string | null;
}

export interface RiskMetrics {
  metrics: BacktestMetrics;
  validation: {
    trade_count: number;
    window_days: number;
    min_trades_required: number;
    min_window_days: number;
    is_reliable: boolean;
  };
  status: "ok" | "degraded";
  reason: string | null;
}

