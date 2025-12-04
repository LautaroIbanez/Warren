/** Cliente API para comunicarse con el backend. */
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchRecommendation(): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/recommendation/today`);
  if (!response.ok) {
    throw new Error(`Failed to fetch recommendation: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchCandles(): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/market/candles`);
  if (!response.ok) {
    throw new Error(`Failed to fetch candles: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchBacktest(): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/backtest/latest`);
  if (!response.ok) {
    throw new Error(`Failed to fetch backtest: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchRiskMetrics(): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/risk/metrics`);
  if (!response.ok) {
    throw new Error(`Failed to fetch risk metrics: ${response.statusText}`);
  }
  return response.json();
}

export async function refreshData(): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/refresh`, {
    method: "POST",
  });
  if (!response.ok) {
    // Intentar parsear el error del backend
    let errorMessage = `Failed to refresh data: ${response.statusText}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        if (typeof errorData.detail === "string") {
          errorMessage = errorData.detail;
        } else if (errorData.detail.message) {
          errorMessage = errorData.detail.message;
          // Incluir información adicional si está disponible
          if (errorData.detail.errors) {
            const errorList = Object.entries(errorData.detail.errors)
              .map(([key, msg]) => `${key}: ${msg}`)
              .join(", ");
            errorMessage += ` (${errorList})`;
          }
        }
      }
    } catch {
      // Si no se puede parsear, usar el mensaje por defecto
    }
    const error = new Error(errorMessage);
    // Agregar información adicional al error para manejo en el componente
    (error as any).status = response.status;
    throw error;
  }
  return response.json();
}

