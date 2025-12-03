/** Panel de métricas de riesgo. */
import type { RiskMetrics } from "../types";

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
          <strong>⚠️ Advertencia:</strong> {reason || "Métricas no confiables - datos insuficientes"}
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
          <div className="metric-value">{metrics.win_rate.toFixed(2)}%</div>
          <div className="metric-hint">Tasa de aciertos</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Profit Factor</div>
          <div className="metric-value">{metrics.profit_factor.toFixed(2)}</div>
          <div className="metric-hint">Ganancia / Pérdida</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Expectancy</div>
          <div className="metric-value">${metrics.expectancy.toFixed(2)}</div>
          <div className="metric-hint">Ganancia esperada por trade</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">CAGR</div>
          <div className="metric-value">{metrics.cagr.toFixed(2)}%</div>
          <div className="metric-hint">Retorno anualizado</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Sharpe Ratio</div>
          <div className="metric-value">{metrics.sharpe_ratio.toFixed(2)}</div>
          <div className="metric-hint">Riesgo ajustado</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Max Drawdown</div>
          <div className="metric-value" style={{ color: metrics.max_drawdown > 20 ? "red" : "inherit" }}>
            {metrics.max_drawdown.toFixed(2)}%
          </div>
          <div className="metric-hint">Máxima caída</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Total Return</div>
          <div className="metric-value" style={{ color: metrics.total_return > 0 ? "green" : "red" }}>
            {metrics.total_return.toFixed(2)}%
          </div>
          <div className="metric-hint">Retorno total</div>
        </div>
      </div>
      <div className="validation-info" style={{ marginTop: "15px", fontSize: "12px", color: "#666" }}>
        {data.data_window && (
          <div>
            Período: {data.data_window.from_date ? new Date(data.data_window.from_date).toLocaleDateString() : "N/A"} 
            - {data.data_window.to_date ? new Date(data.data_window.to_date).toLocaleDateString() : "N/A"}
            {metrics.period_years && ` (${metrics.period_years.toFixed(2)} años)`}
          </div>
        )}
        <div>Ventana: {validation.window_days} días | Trades: {validation.trade_count}</div>
        <div>Estado: <strong style={{ color: isReliable ? "green" : "orange" }}>{status.toUpperCase()}</strong></div>
        {cache_info && (
          <div style={{ marginTop: "5px", fontSize: "11px" }}>
            {cache_info.cached ? (
              <span style={{ color: "#28a745" }}>✓ Cache válido</span>
            ) : (
              <span style={{ color: "#17a2b8" }}>↻ Recomputado</span>
            )}
            {cacheValidation?.cached_hash && (
              <span style={{ marginLeft: "10px", color: "#999" }}>
                Hash: {cacheValidation.cached_hash.substring(0, 8)}...
              </span>
            )}
          </div>
        )}
        {reason && (
          <div style={{ color: "orange", marginTop: "5px" }}>
            ⚠️ {reason}
          </div>
        )}
      </div>
    </div>
  );
}

