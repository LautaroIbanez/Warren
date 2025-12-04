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
      // Limpiar datos previos antes de cargar nuevos
      setData([]);
      setMetadata(null);
      
      const result = await fetchCandles();
      setData(result.candles || []);
      setMetadata(result.metadata || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const updateData = (newData: Candle[] | null, newMetadata: any = null, newError: string | null = null) => {
    setData(newData || []);
    setMetadata(newMetadata);
    setError(newError);
    setLoading(false);
  };

  return { data, loading, error, metadata, refetch: loadCandles, updateData };
}

