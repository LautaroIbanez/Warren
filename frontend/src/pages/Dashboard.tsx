/** Página principal del dashboard. */
import { useState } from "react";
import { useRecommendation } from "../hooks/useRecommendation";
import { useCandles } from "../hooks/useCandles";
import { useBacktestTrades } from "../hooks/useBacktestTrades";
import { useRiskMetrics } from "../hooks/useRiskMetrics";
import { MarketChart } from "../components/MarketChart";
import { RiskPanel } from "../components/RiskPanel";
import { refreshData } from "../api/client";

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
      
      // Limpiar datos previos antes de refrescar
      // Esto asegura que no se reutilicen series viejas
      
      await refreshData();
      
      // Refrescar todos los datos secuencialmente para asegurar sincronización
      await recommendation.refetch();
      await candles.refetch();
      await backtest.refetch();
      await risk.refetch();
      
      // Verificar sincronización de hashes después del refresh
      if (recommendation.data?.candles_hash && candles.metadata?.candles_hash) {
        if (recommendation.data.candles_hash !== candles.metadata.candles_hash) {
          setRefreshError("Advertencia: Los datos de recomendación y velas no están sincronizados. Por favor, refresca nuevamente.");
        }
      }
    } catch (err) {
      setRefreshError(err instanceof Error ? err.message : "Error al refrescar");
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
            
            {/* Alerta de señal bloqueada */}
            {recommendation.data.is_blocked && (
              <div style={{ 
                background: "#f8d7da", 
                padding: "15px", 
                marginBottom: "15px", 
                borderRadius: "4px",
                borderLeft: "4px solid #dc3545"
              }}>
                <strong>🚫 Señal Bloqueada:</strong>
                <p style={{ margin: "5px 0 0 0", fontSize: "14px" }}>
                  {recommendation.data.block_reason || "Backtest muestra rendimiento negativo"}
                </p>
                <p style={{ margin: "5px 0 0 0", fontSize: "12px", color: "#666" }}>
                  {recommendation.data.rationale}
                </p>
              </div>
            )}
            
            {/* Alerta de señal stale */}
            {recommendation.data.is_stale_signal && !recommendation.data.is_blocked && (
              <div style={{ 
                background: "#fff3cd", 
                padding: "15px", 
                marginBottom: "15px", 
                borderRadius: "4px",
                borderLeft: "4px solid #ffc107"
              }}>
                <strong>⚠️ Señal Antigua:</strong>
                <p style={{ margin: "5px 0 0 0", fontSize: "14px" }}>
                  {recommendation.data.stale_reason || "No hay nuevas velas disponibles"}
                </p>
              </div>
            )}
            
            {!recommendation.data.is_blocked && (
              <div style={{ fontSize: "24px", marginBottom: "15px" }}>
                <span
                  style={{
                    color: getSignalColor(recommendation.data.signal),
                    fontWeight: "bold",
                    marginRight: "10px",
                  }}
                >
                  {recommendation.data.signal}
                </span>
                <span>Confianza: {(recommendation.data.confidence * 100).toFixed(1)}%</span>
              </div>
            )}
            {recommendation.data.entry_price && (
              <div style={{ marginBottom: "10px" }}>
                <strong>Entry:</strong> ${recommendation.data.entry_price.toFixed(2)}
                {recommendation.data.stop_loss && (
                  <> | <strong>SL:</strong> ${recommendation.data.stop_loss.toFixed(2)}</>
                )}
                {recommendation.data.take_profit && (
                  <> | <strong>TP:</strong> ${recommendation.data.take_profit.toFixed(2)}</>
                )}
              </div>
            )}
            <div style={{ fontSize: "14px", color: "#666", marginTop: "10px" }}>
              {recommendation.data.rationale}
            </div>
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
            {recommendation.data.as_of && (
              <div style={{ fontSize: "12px", color: "#999", marginTop: "5px" }}>
                Última actualización: {new Date(recommendation.data.as_of).toLocaleString()}
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

