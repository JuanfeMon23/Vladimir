import type { ResultTemplateFormulaProblem } from '../types/result-templates'

/**
 * Un problema de fórmula del backend (`details.problems` al guardar un
 * analito, `details.invalid_formula` al publicar) en español, según su
 * `reason` y los códigos implicados; si no se reconoce, el mensaje del backend.
 */
export function describeFormulaProblem(problem: Pick<ResultTemplateFormulaProblem, 'reason' | 'message' | 'codes'>): string {
  const codes = problem.codes ?? []
  if (codes.length) {
    switch (problem.reason) {
      case 'unknown_code': return `Códigos que no son analitos de esta versión: ${codes.join(', ')}.`
      case 'inactive_code': return `Analitos inactivos en la fórmula: ${codes.join(', ')}.`
      case 'cycle': return `Referencia circular: ${codes.join(' → ')}.`
    }
  }
  return problem.message
}

/** Mensajes del 422 de guardar un analito (`details = { field: "formula", problems }`); `[]` si no es de la fórmula. */
export function formulaProblemMessages(details: unknown): string[] {
  if (!details || typeof details !== 'object') return []
  const { field, problems } = details as { field?: unknown, problems?: unknown }
  if (field !== 'formula' || !Array.isArray(problems)) return []
  return problems.map(problem => describeFormulaProblem(problem as ResultTemplateFormulaProblem))
}
