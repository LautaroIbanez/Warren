/** Hook para obtener recomendación diaria. */
import { useState, useEffect } from "react";
import { fetchRecommendation } from "../api/client";
import type { Recommendation } from "../types";

export function useRecommendation() {
  const [data, setData] = useState<Recommendation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRecommendation();
  }, []);

  const loadRecommendation = async () => {
    try {
      setLoading(true);
      setError(null);
      // Limpiar datos previos antes de cargar nuevos
      setData(null);
      
      const result = await fetchRecommendation();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const updateData = (newData: Recommendation | null, newError: string | null = null) => {
    setData(newData);
    setError(newError);
    setLoading(false);
  };

  return { data, loading, error, refetch: loadRecommendation, updateData };
}

