import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiError } from '~/testing/apiError'
import { fakeCatalogs } from '~/testing/catalogs'
import { ALL_SAMPLES_TAGS } from '~/testing/session'
import { signInWith } from '#leo-client/testing/session'
import { control, fieldError, flushAll, optionLabels, setValue, submitForm } from '#andromeda/testing/dom'
import type { SampleTypeRead } from '../types/samples'
import SampleTypeFormModal from './SampleTypeFormModal.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const TYPE: SampleTypeRead = {
  id: 't1', sample_id: 's1', code: 'SST', name: 'Tubo SST', specimen: 'suero', cap_color_hex: '#F97316',
  is_active: true, created_at: '2026-11-08T00:00:00Z', updated_at: '2026-11-08T00:00:00Z'
}

beforeEach(() => {
  signInWith([...ALL_SAMPLES_TAGS, MODULE_VIEW.catalogs.tag])
  fake.reset()
  fakeCatalogs(fake, ['specimen-types'])
  document.body.innerHTML = ''
})

async function mountModal(entity: SampleTypeRead | null) {
  await mountSuspended(SampleTypeFormModal, { props: { open: true, sampleId: 's1', entity }, attachTo: document.body })
  await flushAll()
  const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
  return { dialog, form: dialog.querySelector('form')! }
}

describe('SampleTypeFormModal: catálogo de especímenes', () => {
  it('los especímenes salen de la API', async () => {
    fake.routes['GET /catalogs/specimen-types'] = [
      { id: 'x', code: 'lcr', name: 'Líquido cefalorraquídeo', sort_order: 0, is_active: true, created_at: '', updated_at: '' }
    ]
    const { dialog } = await mountModal(null)
    expect(optionLabels(control<HTMLSelectElement>(dialog, 'Espécimen'))).toEqual(['Seleccionar espécimen', 'Líquido cefalorraquídeo'])
  })

  it.each([
    ['invalid_reference', 'El espécimen «zzz» no existe.'],
    ['inactive_reference', 'El espécimen «suero» está inactivo.']
  ])('el 422 %s se muestra en Espécimen', async (code, message) => {
    fake.failures['PATCH /sample-types/t1'] = apiError({ code, message, details: { specimen: 'suero' } }, 422)
    const { dialog, form } = await mountModal(TYPE)
    await setValue(control(dialog, 'Nombre'), 'Tubo SST 2')
    await submitForm(form)
    expect(fieldError(dialog, 'Espécimen')).toBe(message)
    expect(fieldError(dialog, 'Nombre')).toBeNull()
  })
})
