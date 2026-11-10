import type { CatalogSlug } from '~/types/catalogs'

/** Tipo de una columna de comportamiento: casilla, entero positivo o decimal positivo. */
export type CatalogFieldKind = 'boolean' | 'integer' | 'decimal'

/** Columna de comportamiento propia de un catálogo (además de código, nombre y orden). */
export interface CatalogExtraField {
  key: string
  label: string
  kind: CatalogFieldKind
  hint?: string
}

export interface CatalogDefinition {
  slug: CatalogSlug
  /** Nombre del catálogo en el selector y el encabezado. */
  label: string
  /** Qué valores guarda y qué módulo los usa. */
  description: string
  /** Texto de "Nuevo …" (con artículo). */
  newLabel: string
  extraFields: CatalogExtraField[]
}

/** Banderas de un tipo de resultado: qué admite y qué exige (no hay lista de códigos en el código). */
const RESULT_TYPE_FIELDS: CatalogExtraField[] = [
  { key: 'uses_option_set', label: 'Usa conjunto de opciones', kind: 'boolean', hint: 'El analito exige un conjunto de opciones y el rango admite una opción esperada.' },
  { key: 'uses_numeric_range', label: 'Rango numérico', kind: 'boolean', hint: 'El rango admite mínimo, máximo y críticos.' },
  { key: 'uses_boolean_range', label: 'Rango booleano', kind: 'boolean', hint: 'El rango admite un valor booleano esperado.' },
  { key: 'uses_unit', label: 'Usa unidad y decimales', kind: 'boolean', hint: 'Unidad y decimales son obligatorios para publicar.' },
  { key: 'uses_formula', label: 'Usa fórmula', kind: 'boolean', hint: 'La fórmula es obligatoria para publicar.' },
  { key: 'requires_reference_range', label: 'Exige rango de referencia', kind: 'boolean', hint: 'Si el analito es reportable, necesita al menos un rango activo para publicar.' }
]

/** Los 9 catálogos de `/api/v1/catalogs/{slug}`, en el orden del selector. */
export const CATALOG_DEFINITIONS: CatalogDefinition[] = [
  { slug: 'consent-document-types', label: 'Tipos de documento a firmar', newLabel: 'Nuevo tipo de documento', description: 'Clasifica los documentos a firmar.', extraFields: [] },
  { slug: 'consent-signers', label: 'Firmantes', newLabel: 'Nuevo firmante', description: 'Quién debe firmar una versión de documento.', extraFields: [] },
  {
    slug: 'duration-units',
    label: 'Unidades de duración',
    newLabel: 'Nueva unidad de duración',
    description: 'Unidades de tiempo de las precondiciones y sus overrides por examen.',
    extraFields: [{ key: 'minutes', label: 'Minutos por unidad', kind: 'integer', hint: 'Cuántos minutos equivale una unidad.' }]
  },
  { slug: 'precondition-kinds', label: 'Tipos de precondición', newLabel: 'Nuevo tipo de precondición', description: 'Raíz o ítem de una precondición.', extraFields: [] },
  { slug: 'precondition-categories', label: 'Categorías de precondición', newLabel: 'Nueva categoría', description: 'Agrupa las precondiciones (ayuno, dieta…).', extraFields: [] },
  { slug: 'specimen-types', label: 'Especímenes', newLabel: 'Nuevo espécimen', description: 'Tipo de espécimen de un tipo de muestra.', extraFields: [] },
  { slug: 'result-types', label: 'Tipos de resultado', newLabel: 'Nuevo tipo de resultado', description: 'Las banderas gobiernan qué admite y qué exige un analito de plantilla.', extraFields: RESULT_TYPE_FIELDS },
  {
    slug: 'sexes',
    label: 'Sexos',
    newLabel: 'Nuevo sexo',
    description: 'Sexo de un rango de referencia.',
    extraFields: [{ key: 'is_wildcard', label: 'Comodín («cualquiera»)', kind: 'boolean', hint: 'Coincide con todos los sexos; a lo sumo uno.' }]
  },
  {
    slug: 'age-units',
    label: 'Unidades de edad',
    newLabel: 'Nueva unidad de edad',
    description: 'Unidad de la edad mínima y máxima de un rango de referencia.',
    extraFields: [{ key: 'days', label: 'Días por unidad', kind: 'decimal', hint: 'Cuántos días equivale una unidad.' }]
  }
]

export function catalogDefinition(slug: string | null | undefined): CatalogDefinition {
  return CATALOG_DEFINITIONS.find(definition => definition.slug === slug) ?? CATALOG_DEFINITIONS[0]!
}

/** `entity_type` de la pestaña Actividad: la tabla del catálogo (el slug con guion bajo). */
export function catalogEntityType(slug: CatalogSlug): string {
  return slug.replaceAll('-', '_')
}
