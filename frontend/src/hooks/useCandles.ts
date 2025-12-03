/** Hook para obtener velas del mercado. */
import { useState, useEffect } from "react";
import { fetchCandles } from "../api/client";
import type { Candle } from "../types";

export function useCandles() {
  const [data, setData] = useState<Candle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<any>(null);

  useEffect(() => {
    loadCandles();
  }, []);

  const loadCandles = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetchCandles();
      setData(result.candles || []);
      setMetadata(result.metadata || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, error, metadata, refetch: loadCandles };
}

