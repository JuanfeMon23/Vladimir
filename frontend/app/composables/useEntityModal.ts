/**
 * Estado del modal "crear / ver-editar" de un listado: si está abierto y qué
 * entidad muestra (`null` = crear). Se pasa a un `<XxxFormModal
 * v-model:open="modal.open" :entity="modal.entity">` de la layer.
 *
 * ```ts
 * const modal = useEntityModal<StaffRead>()
 * modal.openCreate()      // botón "Nuevo"
 * modal.openEdit(row)     // botón "Ver / Editar" de una fila
 * ```
 */
export function useEntityModal<T>() {
  const open = ref(false)
  const entity = shallowRef<T | null>(null)

  function openCreate() {
    entity.value = null
    open.value = true
  }

  function openEdit(value: T) {
    entity.value = value
    open.value = true
  }

  return reactive({ open, entity, openCreate, openEdit })
}

/**
 * Abre el modal de una entidad indicada en la URL (`/<modulo>?open=<id>`) al
 * montar el listado, y quita el parámetro. Lo usan los editores de versión
 * (página propia) para volver al detalle de la entidad en su modal.
 */
export function useOpenEntityFromQuery<T>(
  modal: { openEdit: (value: T) => void },
  get: (id: string) => Promise<T>,
  key = 'open'
) {
  const route = useRoute()
  const router = useRouter()

  onMounted(async () => {
    const id = route.query[key]
    if (typeof id !== 'string' || !id) return
    const { [key]: _removed, ...rest } = route.query
    router.replace({ query: rest })
    try {
      modal.openEdit(await get(id))
    } catch {
      // Si la entidad ya no existe, el listado queda como está.
    }
  })
}
