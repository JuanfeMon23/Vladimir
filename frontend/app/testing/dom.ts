import { nextTick } from 'vue'

/**
 * Consultas y acciones sobre el DOM real para tests de componentes que se
 * teletransportan a `body` (`UiModal`): buscan como lo haría el usuario, por
 * texto visible y por la asociación label → control de `UiFormField`.
 * Solo tests; Nuxt no auto-importa `app/testing/`.
 */

/** Espera a que se asienten promesas y renders encadenados. */
export async function flushAll(rounds = 3) {
  for (let round = 0; round < rounds; round++) {
    for (let i = 0; i < 5; i++) await nextTick()
    await new Promise(resolve => setTimeout(resolve, 0))
  }
}

function labelFor(root: ParentNode, text: string) {
  const label = [...root.querySelectorAll('label')].find(el => el.textContent?.replace('*', '').trim() === text)
  if (!label) throw new Error(`No hay un label "${text}"`)
  return label
}

/** Control (`input`/`select`/`textarea`) asociado al label con ese texto. */
export function control<T extends HTMLElement = HTMLInputElement>(root: ParentNode, label: string): T {
  const el = labelFor(root, label)
  const id = el.getAttribute('for')
  const target = id ? document.getElementById(id) : el.querySelector('input, select, textarea')
  if (!target) throw new Error(`El label "${label}" no tiene control`)
  return target as T
}

/** Mensaje de error (o null) del `UiFormField` cuyo label tiene ese texto. */
export function fieldError(root: ParentNode, label: string) {
  return labelFor(root, label).parentElement?.querySelector('[role="alert"]')?.textContent?.trim() ?? null
}

/** Escribe en un input/textarea o elige en un select, como el usuario. */
export async function setValue(el: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement, value: string) {
  el.value = value
  el.dispatchEvent(new Event(el instanceof HTMLSelectElement ? 'change' : 'input', { bubbles: true }))
  await flushAll(1)
}

/** Marca/desmarca un checkbox (por su label) como el usuario. */
export async function setChecked(root: ParentNode, label: string, checked: boolean) {
  const input = control(root, label)
  if (input.checked === checked) return
  input.checked = checked
  input.dispatchEvent(new Event('change', { bubbles: true }))
  await flushAll(1)
}

/** Botón con ese texto visible (el primero). */
export function button(root: ParentNode, text: string) {
  const found = [...root.querySelectorAll('button')].find(el => el.textContent?.trim() === text)
  if (!found) throw new Error(`No hay un botón "${text}"`)
  return found
}

export async function click(el: HTMLElement) {
  el.click()
  await flushAll()
}

/** `<section>` de `UiSection` con ese título. */
export function section(root: ParentNode, title: string) {
  const heading = [...root.querySelectorAll('h3')].find(el => el.textContent?.trim() === title)
  const found = heading?.closest('section')
  if (!found) throw new Error(`No hay una sección "${title}"`)
  return found
}

/** Textos de las opciones de un select. */
export function optionLabels(select: HTMLSelectElement) {
  return [...select.options].map(option => option.textContent?.trim() ?? '')
}

/** Envía un formulario (como Enter o el botón Guardar). */
export async function submitForm(form: HTMLFormElement) {
  form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  await flushAll()
}

/** Contenedor (por defecto la fila `li` de `UiItemList`) del label con ese texto. */
export function rowOf(root: ParentNode, label: string, selector = 'li'): HTMLElement {
  const found = labelFor(root, label).closest<HTMLElement>(selector)
  if (!found) throw new Error(`El label "${label}" no está dentro de "${selector}"`)
  return found
}

/** Si existe la fila de `UiItemList` con ese label. */
export function hasRow(root: ParentNode, label: string) {
  return [...root.querySelectorAll('li label')].some(el => el.textContent?.trim() === label)
}

/** Visible para el usuario: ni él ni un ancestro con `display: none` (`v-show`). */
export function isShown(el: Element | null) {
  for (let node = el; node; node = node.parentElement) {
    if ((node as HTMLElement).style?.display === 'none') return false
  }
  return Boolean(el)
}
