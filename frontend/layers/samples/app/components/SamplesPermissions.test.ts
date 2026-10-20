import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import DefaultLayout from '~/layouts/default.vue'
import { button, control, flushAll, setChecked, setValue } from '~/testing/dom'
import { fakePage } from '~/testing/fakeApi'
import { ALL_SAMPLES_TAGS, signInWith } from '~/testing/session'
import type { SampleRead, SampleTypeRead } from '../types/samples'
import SampleFormModal from './SampleFormModal.vue'
import SampleTypeFormModal from './SampleTypeFormModal.vue'
import SamplesPage from '../pages/samples/index.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const TYPE: SampleTypeRead = {
  id: 't1', sample_id: 's1', code: 'SST', name: 'Tubo SST', specimen: 'suero', cap_color_hex: '#F97316',
  is_active: true, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z'
}
const SAMPLE: SampleRead = {
  id: 's1', code: 'SUERO', name: 'Suero', description: null, is_active: true,
  created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z', types: [TYPE]
}

const VIEW = 'vladimir.samples.view'
const EDIT = 'vladimir.samples.edit'
const STATUS = 'vladimir.samples.change-status'
const ADD_TYPE = 'vladimir.samples.add-type'

beforeEach(() => {
  fake.reset()
  invalidateCaches()
  clearNuxtData()
  document.body.innerHTML = ''
  fake.routes['GET /samples'] = fakePage([SAMPLE])
  fake.routes['GET /samples/s1'] = SAMPLE
})

async function mountPage(tags: string[]) {
  signInWith(tags)
  const wrapper = await mountSuspended(SamplesPage)
  await flushAll()
  await wrapper.find('button[aria-expanded]').trigger('click')
  await flushAll()
  return wrapper
}

async function mountModal(tags: string[], entity: SampleRead | null = SAMPLE) {
  signInWith(tags)
  await mountSuspended(SampleFormModal, { props: { open: true, entity }, attachTo: document.body })
  await flushAll()
  const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
  return { dialog, form: dialog.querySelector('form')! }
}

const patches = () => fake.requests.mock.calls.filter(([method]) => method === 'PATCH')
async function submit(form: HTMLFormElement) {
  form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  await flushAll()
}

describe('ruta y menú de samples', () => {
  it('la página exige el tag view', () => {
    expect((useRouter().resolve('/samples').meta as { leo?: { tag?: string } }).leo?.tag).toBe(VIEW)
  })

  it('el ítem "Muestras" aparece con view y no sin él', async () => {
    signInWith([VIEW])
    const withView = await mountSuspended(DefaultLayout)
    expect(withView.findAll('a').find(a => a.text() === 'Muestras')?.attributes('href')).toBe('/samples')

    signInWith([ADD_TYPE])
    expect((await mountSuspended(DefaultLayout)).findAll('a').map(a => a.text())).not.toContain('Muestras')
  })
})

describe('listado de muestras', () => {
  it('"Nueva muestra" exige create', async () => {
    expect((await mountPage([VIEW])).text()).not.toContain('Nueva muestra')
    expect((await mountPage([VIEW, 'vladimir.samples.create'])).text()).toContain('Nueva muestra')
  })

  it('solo con view la acción es "Ver"; con edit, "Ver / Editar"', async () => {
    expect((await mountPage([VIEW])).findAll('button').map(b => b.text())).not.toContain('Ver / Editar')
    expect((await mountPage([VIEW, EDIT])).findAll('button').map(b => b.text())).toContain('Ver / Editar')
  })
})

describe('detalle/edición de una muestra', () => {
  it('con solo view es de lectura: campos bloqueados, "Cerrar", sin "Activa" ni "Agregar tipo"', async () => {
    const { dialog } = await mountModal([VIEW])
    expect(dialog.textContent).not.toContain('Guardar cambios')
    expect(dialog.textContent).not.toContain('Agregar tipo')
    expect(dialog.textContent).not.toContain('Activa')
    expect(() => button(dialog, 'Cerrar')).not.toThrow()
    expect(control(dialog, 'Nombre').disabled).toBe(true)
  })

  it('"Agregar tipo" exige add-type', async () => {
    expect((await mountModal([VIEW, EDIT])).dialog.textContent).not.toContain('Agregar tipo')
    document.body.innerHTML = ''
    expect((await mountModal([VIEW, ADD_TYPE])).dialog.textContent).toContain('Agregar tipo')
  })

  it('con edit el PATCH lleva los datos y no is_active', async () => {
    const { dialog, form } = await mountModal([VIEW, EDIT])
    await setValue(control(dialog, 'Nombre'), 'Suero humano')
    await submit(form)
    const [, path, body] = patches()[0]!
    expect(path).toBe('/samples/s1')
    expect(body).toMatchObject({ name: 'Suero humano', code: 'SUERO' })
    expect(body).not.toHaveProperty('is_active')
  })

  it('con solo change-status el PATCH lleva solo el estado y el motivo', async () => {
    const { dialog, form } = await mountModal([VIEW, STATUS])
    expect(control(dialog, 'Nombre').disabled).toBe(true)
    await setChecked(dialog, 'Activa', false)
    await setValue(control(dialog, 'Motivo de la desactivación'), 'Obsoleta')
    await submit(form)
    expect(patches()[0]![2]).toEqual({ is_active: false, activity_reason: 'Obsoleta' })
  })

  it('el formulario completo de la sesión de prueba permite guardar', async () => {
    expect((await mountModal(ALL_SAMPLES_TAGS)).dialog.textContent).toContain('Guardar cambios')
  })
})

describe('edición de un tipo de muestra', () => {
  async function mountType(tags: string[]) {
    signInWith(tags)
    await mountSuspended(SampleTypeFormModal, { props: { open: true, sampleId: 's1', entity: TYPE }, attachTo: document.body })
    await flushAll()
    const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
    return { dialog, form: dialog.querySelector('form')! }
  }

  it('con solo view es de lectura', async () => {
    const { dialog } = await mountType([VIEW])
    expect(control(dialog, 'Nombre').disabled).toBe(true)
    expect(dialog.textContent).not.toContain('Guardar cambios')
    expect(dialog.textContent).not.toContain('Activo')
  })

  it('editar un tipo usa edit (no add-type) y no envía is_active', async () => {
    const { dialog, form } = await mountType([VIEW, EDIT])
    await setValue(control(dialog, 'Nombre'), 'SST II')
    await submit(form)
    const [, path, body] = patches()[0]!
    expect(path).toBe('/sample-types/t1')
    expect(body).toMatchObject({ name: 'SST II' })
    expect(body).not.toHaveProperty('is_active')
  })

  it('con solo change-status el PATCH del tipo lleva solo el estado', async () => {
    const { dialog, form } = await mountType([VIEW, STATUS])
    await setChecked(dialog, 'Activo', false)
    await submit(form)
    expect(patches()[0]![2]).toEqual({ is_active: false })
  })
})
