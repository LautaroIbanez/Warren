/** Componente de gráfico de velas con marcadores de trades. */
import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { Candle, Trade, Recommendation } from "../types";
import { formatCurrency } from "../utils/formatting";

interface MarketChartProps {
  candles: Candle[];
  trades: Trade[];
  recommendation: Recommendation | null;
  candlesMetadata?: {
    latest_candle_timestamp?: string;
    candles_hash?: string;
  };
}

export function MarketChart({ candles, trades, recommendation, candlesMetadata }: MarketChartProps) {
  // Preparar datos para el gráfico (precio de cierre)
  const chartData = useMemo(() => {
    return candles.map((candle) => ({
      timestamp: new Date(candle.timestamp).getTime(),
      time: new Date(candle.timestamp).toLocaleDateString(),
      close: candle.close,
      high: candle.high,
      low: candle.low,
    }));
  }, [candles]);

  // Usar SL/TP de la recomendación actual, no del último trade
  const slLevel = recommendation?.stop_loss || null;
  const tpLevel = recommendation?.take_profit || null;
  
  // Validar sincronización temporal entre recomendación y última vela
  const syncWarning = useMemo(() => {
    if (!recommendation?.signal_timestamp || !candlesMetadata?.latest_candle_timestamp) {
      return null;
    }
    
    const signalTime = new Date(recommendation.signal_timestamp).getTime();
    const candleTime = new Date(candlesMetadata.latest_candle_timestamp).getTime();
    const diffMs = Math.abs(signalTime - candleTime);
    const diffDays = diffMs / (1000 * 60 * 60 * 24);
    
    // Permitir diferencia de hasta 1 día (1 intervalo para velas diarias)
    if (diffDays > 1) {
      return `Desincronización: La recomendación usa datos de ${new Date(recommendation.signal_timestamp).toLocaleString()}, pero la última vela es de ${new Date(candlesMetadata.latest_candle_timestamp).toLocaleString()}`;
    }
    
    return null;
  }, [recommendation, candlesMetadata]);

  // Los marcadores de trades se muestran en la leyenda debajo del gráfico

  if (chartData.length === 0) {
    return <div className="chart-placeholder">No hay datos para mostrar</div>;
  }

  return (
    <div style={{ width: "100%", marginTop: "20px" }}>
      {/* Alerta de desincronización */}
      {syncWarning && (
        <div style={{ 
          background: "#fff3cd", 
          padding: "10px", 
          marginBottom: "15px", 
          borderRadius: "4px",
          borderLeft: "4px solid #ffc107"
        }}>
          <strong>⚠️ Advertencia de Sincronización:</strong>
          <p style={{ margin: "5px 0 0 0", fontSize: "14px" }}>{syncWarning}</p>
        </div>
      )}
      
      {/* Información de timestamps */}
      <div style={{ fontSize: "12px", color: "#999", marginBottom: "10px" }}>
        {recommendation?.signal_timestamp && (
          <span>Señal basada en: {new Date(recommendation.signal_timestamp).toLocaleString()}</span>
        )}
        {candlesMetadata?.latest_candle_timestamp && (
          <span style={{ marginLeft: "15px" }}>
            Última vela: {new Date(candlesMetadata.latest_candle_timestamp).toLocaleString()}
          </span>
        )}
      </div>
      
      <div style={{ height: "500px" }}>
        <ResponsiveContainer>
          <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 80 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 12 }}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis domain={["auto", "auto"]} />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length > 0) {
                  const data = payload[0].payload;
                  return (
                    <div className="chart-tooltip" style={{ background: "white", padding: "10px", border: "1px solid #ccc" }}>
                      <p><strong>Fecha:</strong> {data.time}</p>
                      <p><strong>Close:</strong> {formatCurrency(data.close)}</p>
                      <p><strong>High:</strong> {formatCurrency(data.high)}</p>
                      <p><strong>Low:</strong> {formatCurrency(data.low)}</p>
                    </div>
                  );
                }
                return null;
              }}
            />
            {/* Línea de precio de cierre */}
            <Line
              type="monotone"
              dataKey="close"
              stroke="#8884d8"
              strokeWidth={2}
              dot={false}
            />
            {/* Stop Loss de recomendación actual */}
            {slLevel && (
              <ReferenceLine
                y={slLevel}
                stroke="red"
                strokeDasharray="5 5"
                label={{ value: `SL: ${formatCurrency(slLevel)} (Recomendación)`, position: "right" }}
              />
            )}
            {/* Take Profit de recomendación actual */}
            {tpLevel && (
              <ReferenceLine
                y={tpLevel}
                stroke="green"
                strokeDasharray="5 5"
                label={{ value: `TP: ${formatCurrency(tpLevel)} (Recomendación)`, position: "right" }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      {/* Leyenda de trades */}
      {trades.length > 0 && (
        <div style={{ marginTop: "10px", fontSize: "12px" }}>
          <strong>Trades históricos:</strong> {trades.length} | 
          {trades.length > 0 && (
            <> Último: {trades[trades.length - 1]?.signal} @ {formatCurrency(trades[trades.length - 1]?.entry_price)}</>
          )}
        </div>
      )}
      
      {/* Nota sobre SL/TP */}
      {recommendation && (slLevel || tpLevel) && (
        <div style={{ marginTop: "5px", fontSize: "11px", color: "#666", fontStyle: "italic" }}>
          SL/TP mostrados corresponden a la recomendación actual ({recommendation.signal}), no a trades históricos
        </div>
      )}
    </div>
  );
}
