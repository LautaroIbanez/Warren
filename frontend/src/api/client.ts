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
    throw new Error(`Failed to refresh data: ${response.statusText}`);
  }
  return response.json();
}

