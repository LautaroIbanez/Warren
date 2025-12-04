/** Hook para obtener trades del backtest. */
import { useState, useEffect } from "react";
import { fetchBacktest } from "../api/client";
import type { Trade } from "../types";

export function useBacktestTrades() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [equityCurve, setEquityCurve] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadBacktest();
  }, []);

  const loadBacktest = async () => {
    try {
      setLoading(true);
      setError(null);
      // Limpiar datos previos antes de cargar nuevos
      setTrades([]);
      setEquityCurve([]);
      setMetrics(null);
      
      const result = await fetchBacktest();
      setTrades(result.trades || []);
      setEquityCurve(result.equity_curve || []);
      setMetrics(result.metrics || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const updateData = (newTrades: Trade[] | null, newEquityCurve: any[] | null, newMetrics: any | null, newError: string | null = null) => {
    setTrades(newTrades || []);
    setEquityCurve(newEquityCurve || []);
    setMetrics(newMetrics);
    setError(newError);
    setLoading(false);
  };

  return {
    trades,
    equityCurve,
    metrics,
    loading,
    error,
    refetch: loadBacktest,
    updateData,
  };
}

