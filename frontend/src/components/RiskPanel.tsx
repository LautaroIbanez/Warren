/** Panel de métricas de riesgo. */
import type { RiskMetrics } from "../types";
import { formatPercent, formatCurrency, formatNumber } from "../utils/formatting";
import { formatHash } from "../utils/hash";

interface RiskPanelProps {
  data: RiskMetrics | null;
  loading: boolean;
  error: string | null;
}

export function RiskPanel({ data, loading, error }: RiskPanelProps) {
  if (loading) {
    return <div className="risk-panel">Cargando métricas...</div>;
  }

  if (error) {
    return <div className="risk-panel error">Error: {error}</div>;
  }

  if (!data) {
    return <div className="risk-panel">No hay datos de riesgo disponibles</div>;
  }

  const { metrics, validation, status, reason, cache_info } = data;
  const isReliable = validation.is_reliable;
  
  // Verificar si cache está stale o inconsistente
  const cacheValidation = cache_info?.cache_validation || cache_info?.previous_cache_validation;
  const isCacheStale = cacheValidation?.is_stale || false;
  const isCacheInconsistent = cacheValidation?.is_inconsistent || false;
  const wasRecomputed = cache_info?.was_recomputed || false;

  return (
    <div className="risk-panel">
      <h3>Métricas de Riesgo</h3>
      
      {/* Advertencia de cache stale/inconsistente */}
      {(isCacheStale || isCacheInconsistent) && (
        <div className="warning-banner" style={{ background: "#fff3cd", padding: "10px", marginBottom: "15px", borderRadius: "4px", borderLeft: "4px solid #ffc107" }}>
          <strong>⚠️ Cache Obsoleto:</strong> {cacheValidation?.reason || "Los datos fueron recomputados"}
          {wasRecomputed && <div style={{ fontSize: "12px", marginTop: "5px" }}>✓ Métricas actualizadas desde backtest más reciente</div>}
        </div>
      )}
      
      {!isReliable && (
        <div className="warning-banner" style={{ background: "#fff3cd", padding: "10px", marginBottom: "15px", borderRadius: "4px" }}>
          <strong>⚠️ Advertencia:</strong>{" "}
          {metrics.total_trades < validation.min_trades_required ? (
            <span>Solo {metrics.total_trades} trades (se necesitan {validation.min_trades_required}+)</span>
          ) : (
            <span>{reason || "Métricas no confiables - datos insuficientes"}</span>
          )}
        </div>
      )}
      <div className="metrics-grid" style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "15px" }}>
        <div className="metric-card">
          <div className="metric-label">Total Trades</div>
          <div className="metric-value">{metrics.total_trades}</div>
          <div className="metric-hint">Mínimo: {validation.min_trades_required}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Win Rate</div>
          <div className="metric-value">{formatPercent(metrics.win_rate)}</div>
          <div className="metric-hint">Tasa de aciertos</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Profit Factor</div>
          <div className="metric-value">
            {metrics.profit_factor === null || metrics.profit_factor === undefined
              ? "∞" 
              : formatNumber(metrics.profit_factor)}
          </div>
          <div className="metric-hint">Ganancia / Pérdida</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Expectancy</div>
          <div className="metric-value">{formatCurrency(metrics.expectancy)}</div>
          <div className="metric-hint">
            Ganancia esperada por trade {metrics.expectancy_units ? `(${metrics.expectancy_units})` : ""}
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">CAGR</div>
          <div className="metric-value">
            {metrics.cagr === null || metrics.cagr === undefined ? "N/A" : formatPercent(metrics.cagr)}
          </div>
          <div className="metric-hint">
            {metrics.cagr_label || (metrics.cagr !== null && metrics.cagr !== undefined ? "Retorno anualizado" : "No disponible")}
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Sharpe Ratio</div>
          <div className="metric-value">
            {metrics.sharpe_ratio === null || metrics.sharpe_ratio === undefined ? "N/A" : formatNumber(metrics.sharpe_ratio)}
          </div>
          <div className="metric-hint">
            {metrics.sharpe_reason || (metrics.sharpe_ratio !== null && metrics.sharpe_ratio !== undefined ? "Riesgo ajustado" : "No disponible")}
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Max Drawdown</div>
          <div className="metric-value" style={{ color: metrics.max_drawdown > 20 ? "red" : "inherit" }}>
            {formatPercent(metrics.max_drawdown)}
          </div>
          <div className="metric-hint">Máxima caída</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Total Return</div>
          <div className="metric-value" style={{ color: metrics.total_return > 0 ? "green" : "red" }}>
            {formatPercent(metrics.total_return)}
          </div>
          <div className="metric-hint">Retorno total</div>
        </div>
      </div>
      <div className="validation-info" style={{ marginTop: "15px", fontSize: "12px", color: "#666" }}>
        {data.backtest_period && (
          <div>
            Período del backtest: {data.backtest_period.from_date ? new Date(data.backtest_period.from_date).toLocaleDateString() : "N/A"} 
            - {data.backtest_period.to_date ? new Date(data.backtest_period.to_date).toLocaleDateString() : "N/A"}
            ({data.backtest_period.window_days} días)
            {metrics.period_years && ` (${metrics.period_years.toFixed(2)} años)`}
          </div>
        )}
        {!data.backtest_period && data.data_window && (
          <div>
            Período: {data.data_window.from_date ? new Date(data.data_window.from_date).toLocaleDateString() : "N/A"} 
            - {data.data_window.to_date ? new Date(data.data_window.to_date).toLocaleDateString() : "N/A"}
            {metrics.period_years && ` (${metrics.period_years.toFixed(2)} años)`}
          </div>
        )}
        <div>Ventana: {validation.window_days} días | Trades: {validation.trade_count}</div>
        <div>Estado: <strong style={{ color: isReliable ? "green" : "orange" }}>{status.toUpperCase()}</strong></div>
        {data.last_updated && (
          <div style={{ marginTop: "5px" }}>
            Última actualización: {new Date(data.last_updated).toLocaleString()}
          </div>
        )}
        {cache_info && (
          <div style={{ marginTop: "5px", fontSize: "11px" }}>
            {cache_info.cached ? (
              <span style={{ color: "#28a745" }}>✓ Cache válido</span>
            ) : (
              <span style={{ color: "#17a2b8" }}>↻ Recomputado</span>
            )}
            {cacheValidation?.cached_hash && (
              <span style={{ marginLeft: "10px", color: "#999", fontFamily: "monospace", fontSize: "11px" }}>
                {formatHash(cacheValidation.cached_hash, "Hash", 8)}
              </span>
            )}
          </div>
        )}
        {reason && (
          <div style={{ color: "orange", marginTop: "5px" }}>
            ⚠️ {reason}
          </div>
        )}
        {(data.candles_hash || data.backtest_hash) && (
          <div style={{ marginTop: "10px", fontSize: "11px", color: "#999", fontFamily: "monospace" }}>
            {data.candles_hash && (
              <div>{formatHash(data.candles_hash, "Hash de velas", 16)}</div>
            )}
            {data.backtest_hash && (
              <div style={{ marginTop: "2px" }}>{formatHash(data.backtest_hash, "Hash de backtest", 16)}</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

