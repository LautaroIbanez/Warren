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
import type { Candle, Trade } from "../types";

interface MarketChartProps {
  candles: Candle[];
  trades: Trade[];
}

export function MarketChart({ candles, trades }: MarketChartProps) {
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

  // Obtener niveles SL/TP del último trade si existe
  const lastTrade = trades.length > 0 ? trades[trades.length - 1] : null;
  const slLevel = lastTrade?.stop_loss;
  const tpLevel = lastTrade?.take_profit;

  // Los marcadores de trades se muestran en la leyenda debajo del gráfico

  if (chartData.length === 0) {
    return <div className="chart-placeholder">No hay datos para mostrar</div>;
  }

  return (
    <div style={{ width: "100%", height: "500px", marginTop: "20px" }}>
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
                    <p><strong>Close:</strong> ${data.close.toFixed(2)}</p>
                    <p><strong>High:</strong> ${data.high.toFixed(2)}</p>
                    <p><strong>Low:</strong> ${data.low.toFixed(2)}</p>
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
          {/* Stop Loss */}
          {slLevel && (
            <ReferenceLine
              y={slLevel}
              stroke="red"
              strokeDasharray="5 5"
              label={{ value: `SL: $${slLevel.toFixed(2)}`, position: "right" }}
            />
          )}
          {/* Take Profit */}
          {tpLevel && (
            <ReferenceLine
              y={tpLevel}
              stroke="green"
              strokeDasharray="5 5"
              label={{ value: `TP: $${tpLevel.toFixed(2)}`, position: "right" }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
      {/* Leyenda de trades */}
      {trades.length > 0 && (
        <div style={{ marginTop: "10px", fontSize: "12px" }}>
          <strong>Trades:</strong> {trades.length} | 
          Último: {lastTrade?.signal} @ ${lastTrade?.entry_price.toFixed(2)}
        </div>
      )}
    </div>
  );
}
