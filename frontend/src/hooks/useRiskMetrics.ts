/** Hook para obtener métricas de riesgo. */
import { useState, useEffect } from "react";
import { fetchRiskMetrics } from "../api/client";
import type { RiskMetrics } from "../types";

export function useRiskMetrics() {
  const [data, setData] = useState<RiskMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRiskMetrics();
  }, []);

  const loadRiskMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetchRiskMetrics();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, error, refetch: loadRiskMetrics };
}

