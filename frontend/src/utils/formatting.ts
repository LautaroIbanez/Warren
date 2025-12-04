/** Utilidades de formateo para valores numéricos. */

/**
 * Formatea un valor como porcentaje con 2 decimales.
 * @param value Valor numérico a formatear
 * @param decimals Número de decimales (default: 2)
 * @returns String formateado con símbolo %
 */
export function formatPercent(value: number | null | undefined, decimals: number = 2): string {
  if (value === null || value === undefined || isNaN(value)) {
    return "N/A";
  }
  return `${value.toFixed(decimals)}%`;
}

/**
 * Formatea un valor como moneda (USD) con 2 decimales.
 * @param value Valor numérico a formatear
 * @param decimals Número de decimales (default: 2)
 * @returns String formateado con símbolo $
 */
export function formatCurrency(value: number | null | undefined, decimals: number = 2): string {
  if (value === null || value === undefined || isNaN(value)) {
    return "N/A";
  }
  return `$${value.toFixed(decimals)}`;
}

/**
 * Formatea un número con un número específico de decimales.
 * @param value Valor numérico a formatear
 * @param decimals Número de decimales (default: 2)
 * @returns String formateado
 */
export function formatNumber(value: number | null | undefined, decimals: number = 2): string {
  if (value === null || value === undefined || isNaN(value)) {
    return "N/A";
  }
  return value.toFixed(decimals);
}

