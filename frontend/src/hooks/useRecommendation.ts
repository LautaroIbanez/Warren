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
      const result = await fetchRecommendation();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, error, refetch: loadRecommendation };
}

