/**
 * Tipos genéricos del contrato de la API, compartidos por todos los módulos.
 */

/** Respuesta paginada estándar del backend. */
export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** Error uniforme del backend (AppError), fuera de los 422 de validación. */
export interface ApiError {
  code: string
  message: string
  details?: unknown
}

/** Parámetros de paginación y búsqueda comunes a los listados. */
export interface PaginationParams {
  page?: number
  page_size?: number
  /** Búsqueda de texto libre (insensible a mayúsculas y tildes; máx. 8 palabras y 100 caracteres). */
  q?: string
}

/** Lo que `usePaginatedList` entrega a `fetchPage`: `q` solo viaja si hay término. */
export interface ListRequestParams {
  page: number
  page_size: number
  q?: string
}
