/** Página principal del dashboard. */
import { useState } from "react";
import { useRecommendation } from "../hooks/useRecommendation";
import { useCandles } from "../hooks/useCandles";
import { useBacktestTrades } from "../hooks/useBacktestTrades";
import { useRiskMetrics } from "../hooks/useRiskMetrics";
import { MarketChart } from "../components/MarketChart";
import { RiskPanel } from "../components/RiskPanel";
import { refreshData } from "../api/client";
import { formatPercent, formatCurrency, formatNumber } from "../utils/formatting";
import { truncateHash, formatHash } from "../utils/hash";

export function Dashboard() {
  const recommendation = useRecommendation();
  const candles = useCandles();
  const backtest = useBacktestTrades();
  const risk = useRiskMetrics();

  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      setRefreshError(null);
      
      // Llamar al endpoint de refresh que retorna snapshots sincronizados
      const refreshResponse = await refreshData();
      
      // Verificar si el refresh fue exitoso
      if (!refreshResponse.refresh?.success) {
        const errorMsg = refreshResponse.refresh?.error || "Error desconocido durante el refresh";
        setRefreshError(`Error en refresh: ${errorMsg}`);
        return;
      }
      
      // Actualizar estado usando snapshots directamente (sin llamadas adicionales)
      const { snapshots, errors } = refreshResponse;
      
      // Actualizar recomendación
      if (snapshots.recommendation) {
        recommendation.updateData(snapshots.recommendation, null);
      } else if (errors?.recommendation) {
        recommendation.updateData(null, errors.recommendation);
      }
      
      // Actualizar candles
      if (snapshots.candles) {
        candles.updateData(
          snapshots.candles.candles || [],
          snapshots.candles.metadata || null,
          null
        );
      } else if (errors?.candles) {
        candles.updateData([], null, errors.candles);
      }
      
      // Actualizar backtest
      if (snapshots.backtest) {
        backtest.updateData(
          snapshots.backtest.trades || [],
          snapshots.backtest.equity_curve || [],
          snapshots.backtest.metrics || null,
          null
        );
      } else if (errors?.backtest) {
        backtest.updateData([], [], null, errors.backtest);
      }
      
      // Actualizar risk
      if (snapshots.risk) {
        risk.updateData(snapshots.risk, null);
      } else if (errors?.risk) {
        risk.updateData(null, errors.risk);
      }
      
      // Verificar sincronización de hashes (deberían coincidir ahora)
      if (snapshots.recommendation?.candles_hash && snapshots.candles?.metadata?.candles_hash) {
        if (snapshots.recommendation.candles_hash !== snapshots.candles.metadata.candles_hash) {
          setRefreshError("Advertencia: Los hashes de recomendación y velas no coinciden después del refresh.");
        }
      }
      
      // Mostrar advertencias si hay errores parciales
      if (errors && Object.keys(errors).length > 0) {
        const errorCount = Object.keys(errors).length;
        const errorList = Object.entries(errors).map(([key, msg]) => `${key}: ${msg}`).join(", ");
        setRefreshError(`Advertencia: ${errorCount} snapshot(s) fallaron: ${errorList}`);
      }
      
    } catch (err) {
      // Manejar errores de red o parsing
      const errorMessage = err instanceof Error ? err.message : "Error desconocido al refrescar";
      setRefreshError(`Error al refrescar: ${errorMessage}`);
    } finally {
      setRefreshing(false);
    }
  };

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case "BUY":
        return "green";
      case "SELL":
        return "red";
      default:
        return "gray";
    }
  };

  return (
    <div className="dashboard" style={{ padding: "20px", maxWidth: "1400px", margin: "0 auto" }}>
      <header style={{ marginBottom: "30px" }}>
        <h1>Warren - Paper Trading Dashboard</h1>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          style={{
            padding: "10px 20px",
            fontSize: "16px",
            backgroundColor: "#007bff",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: refreshing ? "not-allowed" : "pointer",
          }}
        >
          {refreshing ? "Refrescando..." : "🔄 Refrescar Datos"}
        </button>
        {refreshError && (
          <div style={{ color: "red", marginTop: "10px" }}>Error: {refreshError}</div>
        )}
      </header>

      {/* Recomendación del día */}
      <section className="recommendation-section" style={{ marginBottom: "30px", padding: "20px", border: "1px solid #ddd", borderRadius: "8px" }}>
        <h2>Recomendación del Día</h2>
        {recommendation.loading ? (
          <div>Cargando recomendación...</div>
        ) : recommendation.error ? (
          <div>
            <div style={{ color: "red", marginBottom: "10px" }}>Error: {recommendation.error}</div>
            {recommendation.error.includes("INSUFFICIENT_DATA") && (
              <div style={{ background: "#fff3cd", padding: "15px", borderRadius: "4px", borderLeft: "4px solid #ffc107" }}>
                <strong>⚠️ Datos Insuficientes</strong>
                <p style={{ margin: "10px 0 0 0" }}>
                  La ventana de datos históricos no cumple con el mínimo requerido (2 años para velas diarias).
                  Por favor, ejecuta múltiples refreshes o espera a acumular más datos históricos.
                </p>
              </div>
            )}
          </div>
        ) : recommendation.data ? (
          <div>
            {/* Advertencia de ventana insuficiente */}
            {recommendation.data.data_window && !recommendation.data.data_window.is_sufficient && (
              <div style={{ background: "#fff3cd", padding: "15px", borderRadius: "4px", borderLeft: "4px solid #ffc107", marginBottom: "15px" }}>
                <strong>⚠️ Ventana de Datos Insuficiente</strong>
                <p style={{ margin: "5px 0 0 0", fontSize: "14px" }}>
                  Ventana actual: {recommendation.data.data_window.window_days} días 
                  (mínimo requerido: 730 días / 2 años)
                </p>
                <p style={{ margin: "5px 0 0 0", fontSize: "12px", color: "#666" }}>
                  Las recomendaciones pueden no ser confiables con datos insuficientes.
                </p>
              </div>
            )}
            
            {/* Alerta de señal bloqueada - Mostrar prominentemente */}
            {recommendation.data.is_blocked && (
              <div style={{ 
                background: "#f8d7da", 
                padding: "20px", 
                marginBottom: "20px", 
                borderRadius: "8px",
                borderLeft: "6px solid #dc3545",
                boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
              }}>
                <div style={{ fontSize: "20px", fontWeight: "bold", color: "#dc3545", marginBottom: "10px" }}>
                  🚫 Señal Bloqueada
                </div>
                {recommendation.data.block_reason && (
                  <div style={{ fontSize: "16px", fontWeight: "600", marginBottom: "10px", color: "#721c24" }}>
                    {recommendation.data.block_reason}
                  </div>
                )}
                {recommendation.data.block_reasons && recommendation.data.block_reasons.length > 1 && (
                  <div style={{ marginTop: "10px", marginBottom: "10px" }}>
                    <div style={{ fontSize: "14px", fontWeight: "600", marginBottom: "5px", color: "#721c24" }}>
                      Razones detalladas:
                    </div>
                    <ul style={{ margin: "5px 0", paddingLeft: "20px", fontSize: "14px", color: "#721c24" }}>
                      {recommendation.data.block_reasons.map((reason, idx) => (
                        <li key={idx} style={{ marginBottom: "5px" }}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {recommendation.data.rationale && (
                  <div style={{ marginTop: "10px", fontSize: "13px", color: "#721c24", lineHeight: "1.5" }}>
                    {recommendation.data.rationale}
                  </div>
                )}
                {(recommendation.data.candles_hash || recommendation.data.backtest_hash) && (
                  <div style={{ marginTop: "10px", fontSize: "11px", color: "#999", fontFamily: "monospace" }}>
                    {recommendation.data.candles_hash && (
                      <div>{formatHash(recommendation.data.candles_hash, "Hash de velas", 16)}</div>
                    )}
                    {recommendation.data.backtest_hash && (
                      <div style={{ marginTop: "2px" }}>{formatHash(recommendation.data.backtest_hash, "Hash de backtest", 16)}</div>
                    )}
                  </div>
                )}
              </div>
            )}
            
            {/* Alerta de señal stale o datos obsoletos - Amarillo (warning) */}
            {(recommendation.data.is_stale_signal || recommendation.data.is_stale) && !recommendation.data.is_blocked && (
              <div style={{ 
                background: "#fff3cd", 
                padding: "15px", 
                marginBottom: "15px", 
                borderRadius: "4px",
                borderLeft: "4px solid #ffc107"
              }}>
                <strong>⚠️ Señal Antigua:</strong>
                <p style={{ margin: "5px 0 0 0", fontSize: "14px" }}>
                  {recommendation.data.stale_reason || recommendation.data.is_stale_signal || "No hay nuevas velas disponibles"}
                </p>
              </div>
            )}
            
            {/* Advertencia de confiabilidad - Amarillo (warning) cuando hay datos pero no son confiables */}
            {risk.data && !risk.data.validation.is_reliable && !recommendation.data.is_blocked && (
              <div style={{ 
                background: "#fff3cd", 
                padding: "15px", 
                marginBottom: "15px", 
                borderRadius: "4px",
                borderLeft: "4px solid #ffc107"
              }}>
                <strong>⚠️ Advertencia de Confiabilidad:</strong>
                {risk.data.metrics.total_trades < risk.data.validation.min_trades_required && (
                  <p style={{ margin: "5px 0 0 0", fontSize: "14px" }}>
                    Solo {risk.data.metrics.total_trades} trades (se necesitan {risk.data.validation.min_trades_required}+)
                  </p>
                )}
                {risk.data.reason && (
                  <p style={{ margin: "5px 0 0 0", fontSize: "13px", color: "#666" }}>
                    {risk.data.reason}
                  </p>
                )}
              </div>
            )}
            
            {/* Banner de Recomendación Activa - Verde/Neutral cuando la señal está permitida */}
            {!recommendation.data.is_blocked && recommendation.data.signal !== "HOLD" && (
              <div style={{ 
                background: "#d4edda", 
                padding: "20px", 
                marginBottom: "20px", 
                borderRadius: "8px",
                borderLeft: "6px solid #28a745",
                boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
              }}>
                <div style={{ fontSize: "20px", fontWeight: "bold", color: "#155724", marginBottom: "15px" }}>
                  ✅ Recomendación Activa
                </div>
                
                {/* Señal y Confianza */}
                <div style={{ marginBottom: "15px" }}>
                  <div style={{ fontSize: "18px", fontWeight: "600", marginBottom: "8px", color: "#155724" }}>
                    Señal: <span style={{ color: getSignalColor(recommendation.data.signal) }}>{recommendation.data.signal}</span>
                  </div>
                  <div style={{ fontSize: "16px", color: "#155724" }}>
                    Confianza: <strong>{formatPercent(recommendation.data.confidence * 100, 1)}</strong>
                  </div>
                </div>
                
                {/* Precios: Entry, SL, TP */}
                {recommendation.data.entry_price && (
                  <div style={{ 
                    display: "grid", 
                    gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", 
                    gap: "15px",
                    marginBottom: "15px",
                    padding: "12px",
                    background: "rgba(255,255,255,0.5)",
                    borderRadius: "4px"
                  }}>
                    <div>
                      <div style={{ fontSize: "12px", color: "#666", marginBottom: "4px" }}>Precio de Entrada</div>
                      <div style={{ fontSize: "16px", fontWeight: "600", color: "#155724" }}>
                        {formatCurrency(recommendation.data.entry_price)}
                      </div>
                    </div>
                    {recommendation.data.stop_loss && (
                      <div>
                        <div style={{ fontSize: "12px", color: "#666", marginBottom: "4px" }}>Stop Loss</div>
                        <div style={{ fontSize: "16px", fontWeight: "600", color: "#dc3545" }}>
                          {formatCurrency(recommendation.data.stop_loss)}
                        </div>
                      </div>
                    )}
                    {recommendation.data.take_profit && (
                      <div>
                        <div style={{ fontSize: "12px", color: "#666", marginBottom: "4px" }}>Take Profit</div>
                        <div style={{ fontSize: "16px", fontWeight: "600", color: "#28a745" }}>
                          {formatCurrency(recommendation.data.take_profit)}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Resumen de Métricas */}
                {risk.data && risk.data.metrics && (
                  <div style={{ 
                    marginTop: "15px", 
                    padding: "12px", 
                    background: "rgba(255,255,255,0.5)",
                    borderRadius: "4px"
                  }}>
                    <div style={{ fontSize: "14px", fontWeight: "600", marginBottom: "8px", color: "#155724" }}>
                      Resumen de Métricas:
                    </div>
                    <div style={{ 
                      display: "grid", 
                      gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", 
                      gap: "10px",
                      fontSize: "13px"
                    }}>
                      <div>
                        <span style={{ color: "#666" }}>Profit Factor:</span>{" "}
                        <strong style={{ color: "#155724" }}>
                          {risk.data.metrics.profit_factor === null || risk.data.metrics.profit_factor === undefined
                            ? "∞" 
                            : formatNumber(risk.data.metrics.profit_factor)}
                        </strong>
                      </div>
                      <div>
                        <span style={{ color: "#666" }}>Win Rate:</span>{" "}
                        <strong style={{ color: "#155724" }}>{formatPercent(risk.data.metrics.win_rate)}</strong>
                      </div>
                      <div>
                        <span style={{ color: "#666" }}>Retorno Total:</span>{" "}
                        <strong style={{ color: risk.data.metrics.total_return > 0 ? "#28a745" : "#dc3545" }}>
                          {formatPercent(risk.data.metrics.total_return)}
                        </strong>
                      </div>
                      <div>
                        <span style={{ color: "#666" }}>Max Drawdown:</span>{" "}
                        <strong style={{ color: risk.data.metrics.max_drawdown > 20 ? "#dc3545" : "#155724" }}>
                          {formatPercent(risk.data.metrics.max_drawdown)}
                        </strong>
                      </div>
                      <div>
                        <span style={{ color: "#666" }}>Total Trades:</span>{" "}
                        <strong style={{ color: "#155724" }}>{risk.data.metrics.total_trades}</strong>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {/* Display para señales HOLD o cuando no hay banner activo */}
            {!recommendation.data.is_blocked && recommendation.data.signal === "HOLD" && (
              <div style={{ fontSize: "24px", marginBottom: "15px", color: "#666" }}>
                <span style={{ fontWeight: "bold", marginRight: "10px" }}>HOLD</span>
                <span>Confianza: {formatPercent(recommendation.data.confidence * 100, 1)}</span>
              </div>
            )}
            {/* Rationale - Solo mostrar si no está bloqueado o si es información adicional */}
            {recommendation.data.rationale && (
              <div style={{ fontSize: "14px", color: "#666", marginTop: "10px", lineHeight: "1.6" }}>
                <strong>Razonamiento:</strong> {recommendation.data.rationale}
              </div>
            )}
            {recommendation.data.data_freshness?.is_stale && (
              <div style={{ color: "orange", marginTop: "10px" }}>
                ⚠️ Datos antiguos: {recommendation.data.data_freshness.reason}
              </div>
            )}
            {recommendation.data.data_window && (
              <div style={{ fontSize: "12px", color: "#999", marginTop: "10px" }}>
                Período: {recommendation.data.data_window.from_date ? new Date(recommendation.data.data_window.from_date).toLocaleDateString() : "N/A"} 
                - {recommendation.data.data_window.to_date ? new Date(recommendation.data.data_window.to_date).toLocaleDateString() : "N/A"} 
                ({recommendation.data.data_window.window_days} días)
              </div>
            )}
            {(recommendation.data.last_updated || recommendation.data.as_of) && (
              <div style={{ fontSize: "12px", color: "#999", marginTop: "5px" }}>
                Última actualización: {new Date(recommendation.data.last_updated || recommendation.data.as_of).toLocaleString()}
              </div>
            )}
            {recommendation.data.backtest_period && (
              <div style={{ fontSize: "12px", color: "#999", marginTop: "5px" }}>
                Período del backtest: {recommendation.data.backtest_period.from_date ? new Date(recommendation.data.backtest_period.from_date).toLocaleDateString() : "N/A"} 
                - {recommendation.data.backtest_period.to_date ? new Date(recommendation.data.backtest_period.to_date).toLocaleDateString() : "N/A"}
                ({recommendation.data.backtest_period.window_days} días)
              </div>
            )}
            {(recommendation.data.candles_hash || recommendation.data.backtest_hash) && (
              <div style={{ fontSize: "11px", color: "#999", marginTop: "5px", fontFamily: "monospace" }}>
                {recommendation.data.candles_hash && (
                  <div>{formatHash(recommendation.data.candles_hash, "Hash de velas", 16)}</div>
                )}
                {recommendation.data.backtest_hash && (
                  <div style={{ marginTop: "2px" }}>{formatHash(recommendation.data.backtest_hash, "Hash de backtest", 16)}</div>
                )}
              </div>
            )}
          </div>
        ) : null}
      </section>

      {/* Panel de riesgo */}
      <section className="risk-section" style={{ marginBottom: "30px", padding: "20px", border: "1px solid #ddd", borderRadius: "8px" }}>
        <RiskPanel data={risk.data} loading={risk.loading} error={risk.error} />
      </section>

      {/* Gráfico de mercado */}
      <section className="chart-section" style={{ padding: "20px", border: "1px solid #ddd", borderRadius: "8px" }}>
        <h2>Gráfico de Mercado</h2>
        {candles.loading ? (
          <div>Cargando gráfico...</div>
        ) : candles.error ? (
          <div style={{ color: "red" }}>Error: {candles.error}</div>
        ) : (
          <MarketChart 
            candles={candles.data} 
            trades={backtest.trades}
            recommendation={recommendation.data}
            candlesMetadata={candles.metadata}
          />
        )}
        {candles.metadata?.freshness?.is_stale && (
          <div style={{ color: "orange", marginTop: "10px" }}>
            ⚠️ {candles.metadata.freshness.reason}
          </div>
        )}
      </section>

      {/* Disclaimer */}
      <footer style={{ marginTop: "40px", padding: "20px", background: "#f8f9fa", borderRadius: "8px", fontSize: "12px", color: "#666" }}>
        <strong>⚠️ IMPORTANTE:</strong> Esta aplicación es solo para análisis y paper trading. No ejecuta órdenes reales.
      </footer>
    </div>
  );
}


