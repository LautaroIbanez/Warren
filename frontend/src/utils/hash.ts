/** Utilidades para formatear y truncar hashes. */

/**
 * Trunca un hash a una longitud específica para mostrar en UI.
 * @param hash Hash completo (SHA256 produce 64 caracteres)
 * @param length Longitud deseada (default: 16)
 * @returns Hash truncado con "..." al final
 */
export function truncateHash(hash: string | null | undefined, length: number = 16): string {
  if (!hash) {
    return "N/A";
  }
  if (hash.length <= length) {
    return hash;
  }
  return `${hash.substring(0, length)}...`;
}

/**
 * Formatea un hash para mostrar en UI con etiqueta.
 * @param hash Hash completo
 * @param label Etiqueta (ej: "Candles", "Backtest")
 * @param length Longitud de truncamiento (default: 16)
 * @returns String formateado
 */
export function formatHash(hash: string | null | undefined, label: string, length: number = 16): string {
  const truncated = truncateHash(hash, length);
  return `${label}: ${truncated}`;
}

