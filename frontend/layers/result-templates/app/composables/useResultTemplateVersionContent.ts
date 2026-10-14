import type { UiSelectOption } from '#andromeda/components/ui/UiSelect.vue'
import type {
  AnalyteRead,
  ReferenceRangeRead,
  ResultOptionSetRead,
  ResultTemplateAnalyteRead,
  ResultTemplateSectionRead,
  UnitRead
} from '../types/result-templates'

/**
 * Contenido editable de una versión de plantilla (secciones, analitos de
 * plantilla) y los catálogos que necesitan sus formularios (analitos,
 * conjuntos de opciones, unidades). Lo crea el editor de versión y lo
 * comparten sus paneles (`ResultTemplateSectionsPanel`,
 * `ResultTemplateAnalytesPanel`).
 *
 * Secciones y analitos se cargan con los inactivos (`include_inactive`) para
 * poder mostrarlos con "Mostrar inactivos" y resolver nombres; los catálogos
 * se cargan completos, pero los selectores (`*OptionsFor`) solo ofrecen los
 * activos más el valor ya elegido.
 */
export function useResultTemplateVersionContent(templateId: string, versionId: string) {
  const api = useResultTemplates()

  const sections = ref<ResultTemplateSectionRead[]>([])
  const sectionsLoading = ref(false)
  const sectionsError = ref<string | null>(null)

  const templateAnalytes = ref<ResultTemplateAnalyteRead[]>([])
  const analytesLoading = ref(false)
  const analytesError = ref<string | null>(null)

  const analyteCatalog = ref<AnalyteRead[]>([])
  const optionSets = ref<ResultOptionSetRead[]>([])
  const units = ref<UnitRead[]>([])
  const catalogError = ref<string | null>(null)
  /** Etiquetas de opciones de resultado ya consultadas (id → etiqueta). */
  const optionLabels = ref(new Map<string, string>())

  function messageOf(err: unknown, fallback: string) {
    return err instanceof Error && err.message ? err.message : fallback
  }

  async function loadSections() {
    sectionsLoading.value = true
    sectionsError.value = null
    try {
      const items = await api.listSections(templateId, versionId, { include_inactive: true })
      sections.value = [...items].sort((a, b) => a.sort_order - b.sort_order)
    } catch (err) {
      sectionsError.value = messageOf(err, 'No se pudieron cargar las secciones.')
    } finally {
      sectionsLoading.value = false
    }
  }

  async function loadAnalytes() {
    analytesLoading.value = true
    analytesError.value = null
    try {
      const items = await api.listTemplateAnalytes(templateId, versionId, { include_inactive: true })
      templateAnalytes.value = [...items].sort((a, b) => a.sort_order - b.sort_order)
    } catch (err) {
      analytesError.value = messageOf(err, 'No se pudieron cargar los analitos.')
    } finally {
      analytesLoading.value = false
    }
  }

  /** Catálogos de los selectores: con caché (5 min; las mutaciones del recurso la invalidan). */
  const catalog = { cacheTtl: CATALOG_CACHE_TTL }

  async function loadCatalogs() {
    catalogError.value = null
    try {
      const [analytes, sets, unitPage] = await Promise.all([
        useAnalytes().list({ page_size: 200 }, catalog),
        useResultOptionSets().list({ page_size: 200 }, catalog),
        useUnits().list({ page_size: 200 }, catalog)
      ])
      analyteCatalog.value = analytes.items
      optionSets.value = sets.items
      units.value = unitPage.items
    } catch (err) {
      catalogError.value = messageOf(err, 'No se pudieron cargar los catálogos de analitos, conjuntos de opciones y unidades.')
    }
  }

  /** Carga las etiquetas de las opciones de los conjuntos dados (para nombrar opciones esperadas). */
  async function loadOptionLabels(optionSetIds: string[]) {
    const pending = [...new Set(optionSetIds)]
    const pages = await Promise.all(
      pending.map(id => useResultOptionSets().listOptions(id, { page_size: 200 }, catalog).catch(() => null))
    )
    const next = new Map(optionLabels.value)
    for (const page of pages) for (const option of page?.items ?? []) next.set(option.id, option.label)
    optionLabels.value = next
  }

  /** Rangos de referencia activos por analito de plantilla (para la vista previa). */
  const referenceRanges = ref<Record<string, ReferenceRangeRead[]>>({})

  /**
   * Carga los rangos activos de los analitos activos y las etiquetas de las
   * opciones de sus conjuntos (vista previa del reporte).
   */
  async function loadReferenceRanges() {
    const active = templateAnalytes.value.filter(item => item.is_active)
    const lists = await Promise.all(
      active.map(item => api.listReferenceRanges(templateId, versionId, item.id))
    )
    referenceRanges.value = Object.fromEntries(active.map((item, index) => [item.id, lists[index] ?? []]))
    await loadOptionLabels(active.flatMap(item => (item.option_set_id ? [item.option_set_id] : [])))
  }

  const analytesById = computed(() => new Map(analyteCatalog.value.map(a => [a.id, a])))
  const optionSetsById = computed(() => new Map(optionSets.value.map(s => [s.id, s])))
  const unitsById = computed(() => new Map(units.value.map(u => [u.id, u])))

  const analyteLabel = (analyte: AnalyteRead) => `${analyte.name} (${analyte.code})`
  const optionSetLabel = (set: ResultOptionSetRead) => `${set.name} (${set.code})`
  const unitLabel = (unit: UnitRead) => `${unit.symbol} — ${unit.name}`

  function sectionOptionsFor(current?: string | null): UiSelectOption[] {
    return activeSelectOptions(sections.value, section => section.name, current)
  }
  function analyteOptionsFor(current?: string | null): UiSelectOption[] {
    return activeSelectOptions(analyteCatalog.value, analyteLabel, current)
  }
  function optionSetOptionsFor(current?: string | null): UiSelectOption[] {
    return activeSelectOptions(optionSets.value, optionSetLabel, current)
  }
  function unitOptionsFor(current?: string | null): UiSelectOption[] {
    return activeSelectOptions(units.value, unitLabel, current)
  }

  function analyteName(analyteId: string) {
    const analyte = analytesById.value.get(analyteId)
    return analyte ? analyteLabel(analyte) : analyteId
  }

  function analyteDefaultUnitId(analyteId: string) {
    return analytesById.value.get(analyteId)?.default_unit_id ?? null
  }

  function templateAnalyteName(templateAnalyteId: string) {
    const item = templateAnalytes.value.find(a => a.id === templateAnalyteId)
    return item ? analyteName(item.analyte_id) : templateAnalyteId
  }

  function sectionName(sectionId: string | null) {
    if (!sectionId) return 'Sin sección'
    return sections.value.find(section => section.id === sectionId)?.name ?? 'Sin sección'
  }

  function optionSetName(optionSetId: string | null) {
    if (!optionSetId) return '—'
    return optionSetsById.value.get(optionSetId)?.name ?? optionSetId
  }

  /** Símbolo de la unidad, o `null` si no tiene / no se conoce. */
  function unitSymbol(unitId: string | null) {
    return unitId ? (unitsById.value.get(unitId)?.symbol ?? null) : null
  }

  function unitName(unitId: string | null) {
    if (!unitId) return '—'
    const unit = unitsById.value.get(unitId)
    return unit ? unit.symbol : unitId
  }

  /** Nombre de un elemento referenciado por un analito (campos de `details.inactive`). */
  function referenceName(field: string, id: string) {
    switch (field) {
      case 'analyte_id': return analyteName(id)
      case 'unit_id': return unitsById.value.get(id) ? unitLabel(unitsById.value.get(id)!) : id
      case 'option_set_id': return optionSetName(id)
      case 'section_id': return sections.value.find(section => section.id === id)?.name ?? id
      case 'expected_option_id': return optionLabels.value.get(id) ?? id
      default: return id
    }
  }

  /**
   * Códigos de los analitos activos de la versión (los que una fórmula puede
   * referenciar), sin el del analito `excludeTemplateAnalyteId` (el propio).
   */
  function formulaCodes(excludeTemplateAnalyteId?: string) {
    return templateAnalytes.value
      .filter(item => item.is_active && item.id !== excludeTemplateAnalyteId)
      .flatMap(item => analytesById.value.get(item.analyte_id)?.code ?? [])
      .sort()
  }

  function isAnalyteActive(analyteId: string) {
    return analytesById.value.get(analyteId)?.is_active ?? true
  }

  function loadAll() {
    return Promise.all([loadSections(), loadAnalytes(), loadCatalogs()])
  }

  return reactive({
    templateId,
    versionId,
    sections,
    sectionsLoading,
    sectionsError,
    templateAnalytes,
    analytesLoading,
    analytesError,
    catalogError,
    units,
    sectionOptionsFor,
    analyteOptionsFor,
    optionSetOptionsFor,
    unitOptionsFor,
    analyteName,
    analyteDefaultUnitId,
    templateAnalyteName,
    sectionName,
    optionSetName,
    unitName,
    unitSymbol,
    referenceName,
    formulaCodes,
    isAnalyteActive,
    loadSections,
    loadAnalytes,
    loadOptionLabels,
    referenceRanges,
    loadReferenceRanges,
    loadAll
  })
}

export type ResultTemplateVersionContent = ReturnType<typeof useResultTemplateVersionContent>
