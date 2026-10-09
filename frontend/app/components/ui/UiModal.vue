<script lang="ts">
/** Pila de modales abiertos: Esc/Tab/foco solo los maneja el superior. */
const openStack: symbol[] = []
</script>

<script setup lang="ts">
/**
 * Modal accesible del núcleo (estilo HeroUI Modal: backdrop con blur, panel
 * con radio grande y sombra, entrada/salida con fade + scale).
 *
 * - `v-model:open` controla la visibilidad.
 * - Cierra con Esc, clic en el backdrop o el botón X (si `dismissable`).
 * - Foco atrapado dentro del panel mientras está abierto; al cerrar vuelve al
 *   elemento que lo abrió.
 * - `role="dialog"`, `aria-modal`, `aria-labelledby` → título.
 * - Bloquea el scroll del `body` mientras está abierto.
 *
 * Es el contenedor estándar para ver/editar/crear entidades desde un listado
 * (ver skill `frontend-reusable-ui`).
 */
export type UiModalSize = 'sm' | 'md' | 'lg' | 'xl'

const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string
    description?: string
    size?: UiModalSize
    /** Si es `false`, no se cierra con Esc, backdrop ni X (p. ej. mientras se guarda). */
    dismissable?: boolean
    hideCloseButton?: boolean
  }>(),
  {
    title: undefined,
    description: undefined,
    size: 'md',
    dismissable: true,
    hideCloseButton: false
  }
)

const emit = defineEmits<{
  'update:open': [value: boolean]
  close: []
}>()

const sizeClasses: Record<UiModalSize, string> = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl'
}

const titleId = useId()
const descriptionId = useId()
const panelRef = ref<HTMLElement | null>(null)
const bodyRef = ref<HTMLElement | null>(null)
let previouslyFocused: HTMLElement | null = null
let pressedOnBackdrop = false
const instanceKey = Symbol('UiModal')

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])'
].join(',')

function focusableIn(root: HTMLElement | null): HTMLElement[] {
  if (!root) return []
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    el => !el.hasAttribute('inert') && el.getClientRects().length > 0
  )
}

function requestClose() {
  if (!props.dismissable) return
  emit('update:open', false)
  emit('close')
}

/** Cierre forzado expuesto en el scope de los slots (p. ej. botón "Cancelar"). */
function close() {
  emit('update:open', false)
  emit('close')
}

function isTopmost() {
  return openStack[openStack.length - 1] === instanceKey
}

function focusFirst() {
  const target = focusableIn(bodyRef.value)[0] ?? focusableIn(panelRef.value)[0] ?? panelRef.value
  target?.focus()
}

// Listeners a nivel de documento mientras está abierto: así Esc y el ciclo de
// Tab funcionan aunque el foco haya caído en <body> (p. ej. un botón que se
// deshabilitó con el foco encima). Solo actúa el modal superior de la pila.
function onDocumentKeydown(event: KeyboardEvent) {
  if (!isTopmost()) return
  if (event.key === 'Escape') {
    event.preventDefault()
    requestClose()
    return
  }
  if (event.key !== 'Tab') return

  const panel = panelRef.value
  const items = focusableIn(panel)
  const active = document.activeElement
  if (items.length === 0) {
    event.preventDefault()
    panel?.focus()
    return
  }
  const first = items[0]!
  const last = items[items.length - 1]!
  if (!panel?.contains(active)) {
    event.preventDefault()
    ;(event.shiftKey ? last : first).focus()
  } else if (event.shiftKey && (active === first || active === panel)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && active === last) {
    event.preventDefault()
    first.focus()
  }
}

function onDocumentFocusin(event: FocusEvent) {
  if (!isTopmost()) return
  const panel = panelRef.value
  if (panel && event.target instanceof Node && !panel.contains(event.target)) focusFirst()
}

function onBackdropPointerDown(event: PointerEvent) {
  pressedOnBackdrop = event.target === event.currentTarget
}

function onBackdropClick(event: MouseEvent) {
  if (pressedOnBackdrop && event.target === event.currentTarget) requestClose()
  pressedOnBackdrop = false
}

function activate() {
  previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null
  if (!openStack.includes(instanceKey)) openStack.push(instanceKey)
  document.body.style.overflow = 'hidden'
  document.addEventListener('keydown', onDocumentKeydown)
  document.addEventListener('focusin', onDocumentFocusin)
}

function deactivate() {
  const index = openStack.indexOf(instanceKey)
  if (index !== -1) openStack.splice(index, 1)
  if (openStack.length === 0) document.body.style.overflow = ''
  document.removeEventListener('keydown', onDocumentKeydown)
  document.removeEventListener('focusin', onDocumentFocusin)
}

function onAfterEnter() {
  focusFirst()
}

function onAfterLeave() {
  previouslyFocused?.focus()
  previouslyFocused = null
}

onMounted(() => {
  if (props.open) activate()
})

watch(
  () => props.open,
  (isOpen) => {
    if (!import.meta.client) return
    if (isOpen) activate()
    else deactivate()
  }
)

onBeforeUnmount(() => {
  if (import.meta.client) deactivate()
})
</script>

<template>
  <Teleport to="body">
    <Transition
      appear
      enter-active-class="transition-opacity duration-200 ease-out *:transition *:duration-200 *:ease-out"
      enter-from-class="opacity-0 *:scale-95 *:opacity-0"
      leave-active-class="transition-opacity duration-150 ease-in *:transition *:duration-150 *:ease-in"
      leave-to-class="opacity-0 *:scale-95 *:opacity-0"
      @after-enter="onAfterEnter"
      @after-leave="onAfterLeave"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-end justify-center bg-default-900/40 p-4 backdrop-blur-sm backdrop-saturate-150 sm:items-center"
        @pointerdown="onBackdropPointerDown"
        @click="onBackdropClick"
      >
        <div
          ref="panelRef"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="title || $slots.header ? titleId : undefined"
          :aria-describedby="description ? descriptionId : undefined"
          tabindex="-1"
          class="flex max-h-[calc(100dvh-2rem)] w-full flex-col overflow-hidden rounded-xl bg-surface shadow-lg outline-none"
          :class="sizeClasses[size]"
        >
          <header class="flex items-start justify-between gap-4 px-6 pb-2 pt-5">
            <div class="min-w-0">
              <div :id="titleId">
                <slot name="header">
                  <h2 v-if="title" class="text-lg font-semibold text-text">
                    {{ title }}
                  </h2>
                </slot>
              </div>
              <p v-if="description" :id="descriptionId" class="mt-0.5 text-sm text-text-muted">
                {{ description }}
              </p>
            </div>
            <button
              v-if="dismissable && !hideCloseButton"
              type="button"
              class="-mr-2 -mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-default-500 transition duration-150 hover:bg-default-100 hover:text-default-700 active:scale-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
              aria-label="Cerrar"
              @click="requestClose"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
              </svg>
            </button>
          </header>

          <div ref="bodyRef" class="flex-1 overflow-y-auto px-6 py-3">
            <slot :close="close" />
          </div>

          <footer v-if="$slots.footer" class="flex flex-wrap items-center justify-end gap-2 px-6 pb-5 pt-3">
            <slot name="footer" :close="close" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
