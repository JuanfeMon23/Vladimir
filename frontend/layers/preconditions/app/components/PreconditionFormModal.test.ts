import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiError } from '~/testing/apiError'
import { fakeCatalogs } from '~/testing/catalogs'
import { ALL_PRECONDITIONS_TAGS } from '~/testing/session'
import { signInWith } from '#leo-client/testing/session'
import { control, fieldError, flushAll, optionLabels, setValue, submitForm } from '#andromeda/testing/dom'
import type { PreconditionRead } from '../types/preconditions'
import PreconditionFormModal from './PreconditionFormModal.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const ROOT: PreconditionRead = {
  id: 'p1', code: 'AYUNO8', name: 'Ayuno de 8 horas', description: null, category: 'ayuno', parent_id: null, kind: 'precondition',
  duration_value: 8, duration_unit: 'horas', patient_instructions: null, is_active: true, items: [],
  created_at: '2026-11-08T00:00:00Z', updated_at: '2026-11-08T00:00:00Z'
}

beforeEach(() => {
  signInWith([...ALL_PRECONDITIONS_TAGS, MODULE_VIEW.catalogs.tag])
  fake.reset()
  fakeCatalogs(fake, ['precondition-categories', 'duration-units'])
  document.body.innerHTML = ''
})

async function mountModal(entity: PreconditionRead | null) {
  await mountSuspended(PreconditionFormModal, { props: { open: true, entity }, attachTo: document.body })
  await flushAll()
  const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
  return { dialog, form: dialog.querySelector('form')! }
}

describe('PreconditionFormModal: catálogos', () => {
  it('categoría y unidad de duración salen de la API', async () => {
    fake.routes['GET /catalogs/precondition-categories'] = [
      { id: 'x', code: 'ayuno', name: 'Ayuno previo', sort_order: 0, is_active: true, created_at: '', updated_at: '' }
    ]
    fake.routes['GET /catalogs/duration-units'] = [
      { id: 'y', code: 'horas', name: 'Horas reloj', sort_order: 0, is_active: true, minutes: 60, created_at: '', updated_at: '' }
    ]
    const { dialog } = await mountModal(null)
    expect(optionLabels(control<HTMLSelectElement>(dialog, 'Categoría'))).toEqual(['Seleccionar categoría', 'Ayuno previo'])
    expect(optionLabels(control<HTMLSelectElement>(dialog, 'Unidad'))).toEqual(['Sin unidad', 'Horas reloj'])
  })

  it('una categoría inactiva ya guardada se muestra con "(inactivo)"', async () => {
    fake.routes['GET /catalogs/precondition-categories'] = [
      { id: 'x', code: 'ayuno', name: 'Ayuno', sort_order: 0, is_active: false, created_at: '', updated_at: '' },
      { id: 'z', code: 'dieta', name: 'Dieta', sort_order: 1, is_active: true, created_at: '', updated_at: '' }
    ]
    const { dialog } = await mountModal(ROOT)
    const select = control<HTMLSelectElement>(dialog, 'Categoría')
    expect(optionLabels(select)).toContain('Ayuno (inactivo)')
    expect(select.value).toBe('ayuno')
  })

  it.each([
    ['category', 'invalid_reference', 'Categoría', 'La categoría «zzz» no existe.'],
    ['category', 'inactive_reference', 'Categoría', 'La categoría «ayuno» está inactiva.'],
    ['duration_unit', 'inactive_reference', 'Unidad', 'La unidad de duración «horas» está inactiva.']
  ])('el 422 en %s (%s) se muestra en el campo %s', async (field, code, label, message) => {
    fake.failures['PATCH /preconditions/p1'] = apiError({ code, message, details: { [field]: 'x' } }, 422)
    const { dialog, form } = await mountModal(ROOT)
    await setValue(control(dialog, 'Nombre'), 'Ayuno de 8 horas (revisado)')
    await submitForm(form)
    expect(fieldError(dialog, label)).toBe(message)
    expect(document.body.querySelector('[role="dialog"]')).not.toBeNull()
  })
})
