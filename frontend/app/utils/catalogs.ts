import type { UiSelectOption } from '#andromeda/components/ui/UiSelect.vue'
import type { CatalogItem } from '~/types/catalogs'

/** Etiqueta de un valor de catálogo: su nombre, o el `code` si no se conoce (o vacío si no hay valor). */
export function catalogNameOf(items: readonly CatalogItem[], code: string | null | undefined): string {
  if (!code) return ''
  return items.find(item => item.code === code)?.name ?? code
}

/**
 * Opciones de un `<UiSelect>` alimentado por un catálogo: solo los activos
 * (en el orden de la API) más el valor actual si está inactivo —con sufijo
 * "(inactivo)"— o si el catálogo no lo trae (p. ej. aún no cargó o no hay
 * permiso de consulta): así el formulario no pierde el valor ya guardado.
 * `value` es el `code`, que es lo que referencian las demás tablas.
 */
export function catalogSelectOptions(
  items: readonly CatalogItem[],
  current?: string | null | readonly (string | null | undefined)[]
): UiSelectOption[] {
  const currentCodes = (Array.isArray(current) ? current : [current]).filter((code): code is string => Boolean(code))
  const options = activeSelectOptions(items.map(item => ({ ...item, id: item.code })), item => item.name, currentCodes)
  const known = new Set(items.map(item => item.code))
  const unknown = currentCodes.filter(code => !known.has(code)).map(code => ({ value: code, label: code }))
  return [...options, ...unknown]
}
