<script setup lang="ts">
/**
 * Pestañas del núcleo (estilo HeroUI Tabs: lista en píldora gris con
 * "cursor" blanco que se desliza a la pestaña activa, o subrayado con
 * indicador de color). Accesible: `role="tablist"`/`tab`/`tabpanel`,
 * `aria-selected`, `aria-controls`, tabindex itinerante y teclado
 * (← → / Home / End con activación automática).
 *
 * El contenido de cada pestaña va en un slot con su `key`
 * (`<template #general>…</template>`). Los paneles se montan la primera vez
 * que se visitan y luego se ocultan con `v-show`, para no perder su estado
 * (formularios a medio llenar) al cambiar de pestaña.
 */
export interface UiTab {
  key: string
  label: string
  disabled?: boolean
}

const active = defineModel<string>({ required: true })

const props = withDefaults(
  defineProps<{
    tabs: UiTab[]
    variant?: 'solid' | 'underlined'
    /** Nombre accesible de la lista de pestañas. */
    ariaLabel?: string
    /** Pestañas a lo ancho del contenedor. */
    fullWidth?: boolean
  }>(),
  {
    variant: 'solid',
    ariaLabel: undefined,
    fullWidth: false
  }
)

const baseId = useId()
const tabId = (key: string) => `${baseId}-tab-${key}`
const panelId = (key: string) => `${baseId}-panel-${key}`

const visited = ref(new Set<string>([active.value]))
watch(active, key => visited.value.add(key))

const listRef = ref<HTMLElement | null>(null)
const tabRefs = new Map<string, HTMLElement>()
function setTabRef(key: string, el: unknown) {
  if (el instanceof HTMLElement) tabRefs.set(key, el)
  else tabRefs.delete(key)
}

// Cursor deslizante: se posiciona sobre la pestaña activa.
const cursor = ref({ left: 0, width: 0, ready: false })
function updateCursor() {
  const el = tabRefs.get(active.value)
  if (!el) return
  cursor.value = { left: el.offsetLeft, width: el.offsetWidth, ready: true }
}

let resizeObserver: ResizeObserver | null = null
onMounted(() => {
  nextTick(updateCursor)
  if (typeof ResizeObserver !== 'undefined' && listRef.value) {
    resizeObserver = new ResizeObserver(() => updateCursor())
    resizeObserver.observe(listRef.value)
  }
})
onBeforeUnmount(() => resizeObserver?.disconnect())
watch([active, () => props.tabs], () => nextTick(updateCursor), { deep: true })

const enabledTabs = computed(() => props.tabs.filter(tab => !tab.disabled))

function select(key: string, focus = false) {
  active.value = key
  if (focus) nextTick(() => tabRefs.get(key)?.focus())
}

function onKeydown(event: KeyboardEvent) {
  const list = enabledTabs.value
  const index = list.findIndex(tab => tab.key === active.value)
  let next: UiTab | undefined
  if (event.key === 'ArrowRight') next = list[(index + 1) % list.length]
  else if (event.key === 'ArrowLeft') next = list[(index - 1 + list.length) % list.length]
  else if (event.key === 'Home') next = list[0]
  else if (event.key === 'End') next = list[list.length - 1]
  if (!next) return
  event.preventDefault()
  select(next.key, true)
}

const listClasses = computed(() =>
  props.variant === 'solid'
    ? 'gap-1 rounded-md bg-default-100 p-1'
    : 'gap-2 border-b border-border'
)

const cursorClasses = computed(() =>
  props.variant === 'solid'
    ? 'top-1 bottom-1 rounded-sm bg-surface shadow-sm'
    : 'bottom-0 h-0.5 rounded-full bg-primary-500'
)

function tabClasses(tab: UiTab) {
  const selected = tab.key === active.value
  const base = 'relative z-10 flex items-center justify-center whitespace-nowrap px-3 text-sm font-medium transition duration-150 outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500 disabled:pointer-events-none disabled:opacity-50'
  const size = props.variant === 'solid' ? 'h-8 rounded-sm active:scale-[0.97]' : 'h-10 rounded-sm'
  const color = selected
    ? props.variant === 'solid' ? 'text-text' : 'text-primary-600'
    : 'text-default-500 hover:text-default-700'
  return [base, size, color, props.fullWidth ? 'flex-1' : '']
}
</script>

<template>
  <div class="space-y-4">
    <div class="overflow-x-auto">
      <div
        ref="listRef"
        role="tablist"
        :aria-label="ariaLabel"
        class="relative flex"
        :class="[listClasses, fullWidth ? 'w-full' : 'w-max']"
        @keydown="onKeydown"
      >
        <span
          v-if="cursor.ready"
          class="absolute z-0 transition-all duration-200 ease-out"
          :class="cursorClasses"
          :style="{ left: `${cursor.left}px`, width: `${cursor.width}px` }"
          aria-hidden="true"
        />
        <button
          v-for="tab in tabs"
          :id="tabId(tab.key)"
          :key="tab.key"
          :ref="el => setTabRef(tab.key, el)"
          type="button"
          role="tab"
          :aria-selected="tab.key === active"
          :aria-controls="panelId(tab.key)"
          :tabindex="tab.key === active ? 0 : -1"
          :disabled="tab.disabled"
          :class="tabClasses(tab)"
          @click="select(tab.key)"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <template v-for="tab in tabs" :key="tab.key">
      <div
        v-if="visited.has(tab.key)"
        v-show="tab.key === active"
        :id="panelId(tab.key)"
        role="tabpanel"
        :aria-labelledby="tabId(tab.key)"
        tabindex="-1"
        class="outline-none"
      >
        <slot :name="tab.key" />
      </div>
    </template>
  </div>
</template>
