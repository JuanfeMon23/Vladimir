import type {
  AgeUnitItem,
  CatalogItem,
  CatalogItemBySlug,
  CatalogSlug,
  DurationUnitItem,
  ResultTypeBehavior,
  ResultTypeItem,
  SexItem
} from '~/types/catalogs'
import { catalogNameOf, catalogSelectOptions } from '../utils/catalogs'
import type { createFakeApi } from './fakeApi'

/**
 * Catálogos de categoría falsos para tests (solo tests; Nuxt no auto-importa
 * `app/testing/`): las mismas filas que siembra el backend, con códigos y
 * etiquetas reales, para que los componentes que llenan selectores o nombran
 * valores desde `GET /catalogs/{slug}` se prueben como en producción.
 */

const STAMPS = { created_at: '2026-11-08T00:00:00Z', updated_at: '2026-11-08T00:00:00Z' }

function row(code: string, name: string, index: number, overrides: Partial<CatalogItem> = {}): CatalogItem {
  return { id: `${code}-id`, code, name, sort_order: index, is_active: true, ...STAMPS, ...overrides }
}

function rows(entries: [code: string, name: string][]): CatalogItem[] {
  return entries.map(([code, name], index) => row(code, name, index))
}

const NO_FLAGS: ResultTypeBehavior = {
  uses_option_set: false,
  uses_numeric_range: false,
  uses_boolean_range: false,
  uses_unit: false,
  uses_formula: false,
  requires_reference_range: false
}

function resultType(code: string, name: string, index: number, flags: Partial<ResultTypeBehavior>): ResultTypeItem {
  return { ...row(code, name, index), ...NO_FLAGS, ...flags }
}

const OPTION_RANGE = { uses_option_set: true, requires_reference_range: true }

export const CATALOG_FIXTURES: { [S in CatalogSlug]: CatalogItemBySlug[S][] } = {
  'consent-document-types': rows([
    ['consentimiento_informado', 'Consentimiento informado de examen'],
    ['tratamiento_datos', 'Tratamiento de datos (general)'],
    ['otro', 'Otro']
  ]),
  'consent-signers': rows([
    ['paciente', 'Paciente'],
    ['paciente_o_representante', 'Paciente o representante']
  ]),
  'duration-units': [
    { ...row('minutos', 'Minutos', 0), minutes: 1 },
    { ...row('horas', 'Horas', 1), minutes: 60 },
    { ...row('dias', 'Días', 2), minutes: 1440 }
  ] satisfies DurationUnitItem[],
  'precondition-kinds': rows([['precondition', 'Precondición'], ['condition', 'Condición']]),
  'precondition-categories': rows([
    ['ayuno', 'Ayuno'],
    ['dieta', 'Dieta'],
    ['alcohol_sustancias', 'Alcohol y sustancias'],
    ['tabaco', 'Tabaco'],
    ['medicamentos', 'Medicamentos'],
    ['actividad_fisica', 'Actividad física'],
    ['abstinencia_sexual', 'Abstinencia sexual'],
    ['recoleccion_muestra', 'Recolección de muestra'],
    ['horario_toma', 'Horario de toma'],
    ['reposo', 'Reposo'],
    ['higiene', 'Higiene'],
    ['otro', 'Otro']
  ]),
  'specimen-types': rows([
    ['suero', 'Suero'],
    ['plasma', 'Plasma'],
    ['sangre_total', 'Sangre total'],
    ['orina', 'Orina'],
    ['heces', 'Heces'],
    ['secrecion', 'Secreción'],
    ['otro', 'Otro']
  ]),
  'result-types': [
    resultType('numeric', 'Numérico', 0, { uses_numeric_range: true, uses_unit: true, requires_reference_range: true }),
    resultType('boolean', 'Booleano', 1, { uses_boolean_range: true, requires_reference_range: true }),
    resultType('qualitative', 'Cualitativo', 2, OPTION_RANGE),
    resultType('semi_quantitative', 'Semicuantitativo', 3, OPTION_RANGE),
    resultType('titer', 'Título (dilución)', 4, OPTION_RANGE),
    resultType('text', 'Texto', 5, {}),
    resultType('calculated', 'Calculado', 6, { uses_numeric_range: true, uses_unit: true, uses_formula: true, requires_reference_range: true })
  ],
  'sexes': [
    { ...row('any', 'Cualquiera', 0), is_wildcard: true },
    { ...row('male', 'Masculino', 1), is_wildcard: false },
    { ...row('female', 'Femenino', 2), is_wildcard: false }
  ] satisfies SexItem[],
  'age-units': [
    { ...row('dias', 'Días', 0), days: 1 },
    { ...row('meses', 'Meses', 1), days: 30.4375 },
    { ...row('anos', 'Años', 2), days: 365.25 }
  ] satisfies AgeUnitItem[]
}

/** Registra en el fake `GET /catalogs/<slug>` de los catálogos pedidos (todos si se omite `slugs`). */
export function fakeCatalogs(fake: ReturnType<typeof createFakeApi>, slugs: readonly CatalogSlug[] = Object.keys(CATALOG_FIXTURES) as CatalogSlug[]) {
  for (const slug of slugs) fake.routes[`GET /catalogs/${slug}`] = CATALOG_FIXTURES[slug]
}

/**
 * Parte de catálogos de un `ResultTemplateVersionContent` falso (tipos de
 * resultado, sexos y unidades de edad), para los tests de formularios de
 * result-templates que reciben `content` por prop. `fixtures` permite probar
 * con filas propias (p. ej. un tipo de resultado nuevo con sus banderas).
 */
export function catalogContentStub(fixtures: { [S in CatalogSlug]?: CatalogItemBySlug[S][] } = {}) {
  const data = { ...CATALOG_FIXTURES, ...fixtures }
  const stub = <S extends CatalogSlug>(slug: S) => ({
    error: null,
    items: data[slug],
    nameOf: (code: string | null | undefined) => catalogNameOf(data[slug], code),
    optionsFor: (current?: string | null) => catalogSelectOptions(data[slug], current)
  })
  return {
    resultTypes: stub('result-types'),
    sexes: stub('sexes'),
    ageUnits: stub('age-units'),
    resultTypeBehavior: (code: string | null | undefined) => data['result-types'].find(item => item.code === code),
    sexLabel: (code: string) => (data.sexes.find(item => item.code === code)?.is_wildcard ? null : catalogNameOf(data.sexes, code))
  }
}
