import type { UiSelectOption } from '~/components/ui/UiSelect.vue'

/**
 * Opciones de un `<UiSelect>` de relación (área, unidad, analito…): solo los
 * elementos activos (no se crean relaciones nuevas con desactivados), más
 * el/los valores ya seleccionados aunque estén inactivos, marcados
 * "(inactivo)" para que el formulario los siga mostrando.
 */
export function activeSelectOptions<T extends { id: string, is_active: boolean }>(
  items: readonly T[],
  label: (item: T) => string,
  current?: string | null | readonly (string | null | undefined)[]
): UiSelectOption[] {
  const keep = new Set((Array.isArray(current) ? current : [current]).filter((id): id is string => Boolean(id)))
  return items
    .filter(item => item.is_active || keep.has(item.id))
    .map(item => ({
      value: item.id,
      label: item.is_active ? label(item) : `${label(item)} (inactivo)`
    }))
}
