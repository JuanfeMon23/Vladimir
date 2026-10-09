/** Límites del parámetro `q` del backend (más allá responde 422). */
export const SEARCH_MAX_LENGTH = 100
export const SEARCH_MAX_WORDS = 8

/**
 * Normaliza lo escrito en un buscador para enviarlo como `q`: recorta,
 * colapsa espacios, y respeta los máximos del backend (8 palabras, 100
 * caracteres). Devuelve `''` si no hay término (no se envía `q`).
 */
export function normalizeSearchTerm(value: unknown): string {
  if (typeof value !== 'string') return ''
  const words = value.trim().split(/\s+/).filter(Boolean).slice(0, SEARCH_MAX_WORDS)
  return words.join(' ').slice(0, SEARCH_MAX_LENGTH).trimEnd()
}
