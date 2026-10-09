import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '~/composables/useApi'
import { fakePage } from '~/testing/fakeApi'
import { button, control, fieldError, flushAll, hasRow, optionLabels, rowOf, section, setChecked, setValue, submitForm } from '~/testing/dom'
import type { LabTestRead } from '../types/lab-tests'
import LabTestFormModal from './LabTestFormModal.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useApi', () => () => fake.api)

// La pila de modales es de módulo: cada test desmonta el suyo.
enableAutoUnmount(afterEach)

const AREAS = [
  { id: 'a1', code: 'HEM', name: 'Hematología', is_active: true },
  { id: 'a2', code: 'QUI', name: 'Química', is_active: true },
  { id: 'a3', code: 'OLD', name: 'Antigua', is_active: false }
]

const PRINT_LABEL_VERSIONS = [
  { id: 'plv1', version_number: 1, status: 'retired' },
  { id: 'plv2', version_number: 2, status: 'published' }
]

function entity(overrides: Partial<LabTestRead> = {}): LabTestRead {
  return {
    id: 't1',
    code: 'GLU',
    name: 'Glucosa',
    abbreviation: null,
    description: null,
    area_id: 'a2',
    method: null,
    turnaround_hours: 24,
    loinc_code: null,
    cups_code: null,
    print_label_version_id: null,
    result_template_version_id: null,
    is_active: true,
    created_at: '2026-10-01T00:00:00Z',
    updated_at: '2026-10-01T00:00:00Z',
    preconditions: [],
    sample_types: [],
    consent_documents: [],
    ...overrides
  }
}

beforeEach(() => {
  fake.reset()
  document.body.innerHTML = ''
  fake.routes['GET /lab-areas'] = fakePage(AREAS)
  fake.routes['GET /print-labels'] = fakePage([{ id: 'pl1', code: 'ETQ', name: 'Etiqueta tubo', is_active: true }])
  // El backend filtra por `status`.
  fake.routes['GET /print-labels/pl1/versions'] = (options: unknown) => fakePage(PRINT_LABEL_VERSIONS.filter(
    version => version.status === (options as { params?: { status?: string } }).params?.status
  ))
  fake.routes['GET /print-label-versions/plv1'] = {
    ...PRINT_LABEL_VERSIONS[0],
    owner: { id: 'pl1', code: 'ETQ', name: 'Etiqueta tubo', is_active: true }
  }
  fake.routes['GET /result-templates'] = fakePage([])
  fake.routes['GET /samples'] = fakePage([{
    id: 's1',
    code: 'SAN',
    name: 'Sangre',
    is_active: true,
    types: [
      { id: 'rojo', code: 'TRO', name: 'Tubo tapa roja', is_active: true },
      { id: 'lila', code: 'TLI', name: 'Tubo tapa lila', is_active: true },
      { id: 'viejo', code: 'OLD', name: 'Tubo viejo', is_active: false }
    ]
  }])
})

const ROJO = 'Tubo tapa roja (TRO · Sangre)'
const LILA = 'Tubo tapa lila (TLI · Sangre)'

/** Datos mínimos válidos de un examen nuevo (sin tipos de muestra). */
async function fillBasics(dialog: HTMLElement) {
  await setValue(control(dialog, 'Código'), 'X')
  await setValue(control(dialog, 'Nombre'), 'X')
  await setValue(control<HTMLSelectElement>(dialog, 'Área'), 'a1')
}

/** Marca el tubo rojo como el tipo de muestra preferido. */
async function pickRojo(dialog: HTMLElement) {
  await setChecked(dialog, ROJO, true)
  await setChecked(rowOf(dialog, ROJO), 'Preferido', true)
}

async function mountModal(lab: LabTestRead | null) {
  const wrapper = await mountSuspended(LabTestFormModal, {
    props: { entity: lab, open: true },
    attachTo: document.body
  })
  await flushAll()
  const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
  return { wrapper, dialog, form: dialog.querySelector('form')! }
}

describe('LabTestFormModal: crear', () => {
  it('ofrece solo áreas activas y envía el POST con el área y la versión de etiqueta elegidas', async () => {
    const { wrapper, dialog, form } = await mountModal(null)

    const area = control<HTMLSelectElement>(dialog, 'Área')
    expect(optionLabels(area)).toEqual(['Seleccionar área', 'Hematología (HEM)', 'Química (QUI)'])

    await setValue(control(dialog, 'Código'), ' CBC ')
    await setValue(control(dialog, 'Nombre'), 'Cuadro hemático')
    await setValue(area, 'a1')
    await setValue(control(dialog, 'Tiempo de entrega (horas)'), '24')
    await pickRojo(dialog)
    await setChecked(dialog, LILA, true)
    await setValue(control(rowOf(dialog, LILA), 'Volumen (mL)'), '2.5')

    const label = section(dialog, 'Etiqueta de impresión')
    await setValue(control<HTMLSelectElement>(label, 'Etiqueta'), 'pl1')
    const version = control<HTMLSelectElement>(label, 'Versión publicada')
    // Solo las publicadas.
    expect(optionLabels(version)).toEqual(['Sin versión', 'Versión 2'])
    await setValue(version, 'plv2')

    await submitForm(form)

    expect(fake.bodies('POST', '/lab-tests')).toEqual([{
      code: 'CBC',
      name: 'Cuadro hemático',
      abbreviation: null,
      area_id: 'a1',
      method: null,
      turnaround_hours: 24,
      loinc_code: null,
      cups_code: null,
      description: null,
      print_label_version_id: 'plv2',
      result_template_version_id: null,
      is_active: true,
      sample_types: [
        { sample_type_id: 'rojo', is_preferred: true, required_volume_ml: null, sort_order: 1 },
        { sample_type_id: 'lila', is_preferred: false, required_volume_ml: 2.5, sort_order: 2 }
      ]
    }])
    expect(wrapper.emitted('saved')).toHaveLength(1)
    expect(wrapper.emitted('update:open')?.at(-1)).toEqual([false])
  })

  it('sin código, nombre ni área no envía y marca los campos', async () => {
    const { wrapper, dialog, form } = await mountModal(null)
    await submitForm(form)
    expect(fake.bodies('POST', '/lab-tests')).toEqual([])
    expect(fieldError(dialog, 'Código')).toBe('El código es obligatorio.')
    expect(fieldError(dialog, 'Nombre')).toBe('El nombre es obligatorio.')
    expect(fieldError(dialog, 'Área')).toBe('Selecciona un área.')
    expect(wrapper.emitted('saved')).toBeUndefined()
  })

  it('ofrece solo los tipos de muestra activos', async () => {
    const { dialog } = await mountModal(null)
    expect(hasRow(dialog, ROJO)).toBe(true)
    expect(hasRow(dialog, LILA)).toBe(true)
    expect(hasRow(dialog, 'Tubo viejo (OLD · Sangre)')).toBe(false)
  })

  it('sin tipo de muestra no envía y avisa en la sección', async () => {
    const { wrapper, dialog, form } = await mountModal(null)
    await fillBasics(dialog)
    await submitForm(form)
    expect(fake.bodies('POST', '/lab-tests')).toEqual([])
    expect(section(dialog, 'Tipos de muestra').textContent).toContain('El examen debe tener al menos un tipo de muestra.')
    expect(wrapper.emitted('saved')).toBeUndefined()
  })

  it('con tipos marcados pero sin preferido no envía; marcar uno preferido desmarca el otro', async () => {
    const { dialog, form } = await mountModal(null)
    await fillBasics(dialog)
    await setChecked(dialog, ROJO, true)
    await submitForm(form)
    expect(fake.bodies('POST', '/lab-tests')).toEqual([])
    expect(section(dialog, 'Tipos de muestra').textContent).toContain('Marca exactamente un tipo de muestra como preferido.')

    await setChecked(rowOf(dialog, ROJO), 'Preferido', true)
    await setChecked(dialog, LILA, true)
    await setChecked(rowOf(dialog, LILA), 'Preferido', true)
    expect(control(rowOf(dialog, ROJO), 'Preferido').checked).toBe(false)
    await submitForm(form)
    expect(fake.bodies('POST', '/lab-tests')).toHaveLength(1)
  })

  it('no tiene pestañas ni campo de motivo al crear', async () => {
    const { dialog } = await mountModal(null)
    expect(dialog.querySelector('[role="tablist"]')).toBeNull()
    await setChecked(dialog, 'Activo', false)
    expect(dialog.textContent).not.toContain('Motivo de la')
  })
})

describe('LabTestFormModal: editar', () => {
  it('PATCH con los valores del examen y sin activity_reason si el estado no cambió', async () => {
    const { wrapper, dialog, form } = await mountModal(entity())
    await setValue(control(dialog, 'Nombre'), 'Glucosa basal')
    await submitForm(form)

    const [body] = fake.bodies('PATCH', '/lab-tests/t1') as Record<string, unknown>[]
    expect(body).toMatchObject({ code: 'GLU', name: 'Glucosa basal', area_id: 'a2', turnaround_hours: 24, is_active: true })
    expect(body).not.toHaveProperty('activity_reason')
    expect(body).not.toHaveProperty('sample_types')
    expect(wrapper.emitted('saved')).toHaveLength(1)
  })

  it('al desactivar pide el motivo y lo envía en el PATCH', async () => {
    const { dialog, form } = await mountModal(entity())
    await setChecked(dialog, 'Activo', false)
    await setValue(control(dialog, 'Motivo de la desactivación'), 'Reemplazado por GLU2')
    await submitForm(form)

    const [body] = fake.bodies('PATCH', '/lab-tests/t1') as Record<string, unknown>[]
    expect(body).toMatchObject({ is_active: false, activity_reason: 'Reemplazado por GLU2' })
  })

  it('la versión de etiqueta asignada se resuelve con su dueña y se conserva aunque esté retirada', async () => {
    const { dialog } = await mountModal(entity({ print_label_version_id: 'plv1' }))
    expect(fake.requests).toHaveBeenCalledWith('GET', '/print-label-versions/plv1', undefined)
    expect(fake.requests).toHaveBeenCalledWith('GET', '/print-labels/pl1/versions', { params: { page_size: 200, status: 'published' }, cacheTtl: CATALOG_CACHE_TTL })
    const label = section(dialog, 'Etiqueta de impresión')
    expect(control<HTMLSelectElement>(label, 'Etiqueta').value).toBe('pl1')
    const version = control<HTMLSelectElement>(label, 'Versión publicada')
    expect(version.value).toBe('plv1')
    expect(optionLabels(version)).toEqual(['Sin versión', 'Versión 1 (retirada)', 'Versión 2'])
  })

  it('muestra el área actual aunque esté inactiva, marcada "(inactivo)"', async () => {
    const { dialog } = await mountModal(entity({ area_id: 'a3' }))
    const area = control<HTMLSelectElement>(dialog, 'Área')
    expect(optionLabels(area)).toContain('Antigua (OLD) (inactivo)')
    expect(area.value).toBe('a3')
  })

  it('tiene las pestañas del detalle y la de actividad', async () => {
    const { dialog } = await mountModal(entity())
    const tabs = [...dialog.querySelectorAll('[role="tab"]')].map(tab => tab.textContent?.trim())
    expect(tabs).toEqual(['General', 'Precondiciones', 'Muestras', 'Documentos', 'Actividad'])
  })
})

describe('LabTestFormModal: errores del backend', () => {
  it.each([
    ['validation_error', 'El examen debe tener al menos un tipo de muestra.', { field: 'sample_types' }],
    ['validation_error', 'Debe haber exactamente un tipo de muestra preferido.', { preferred_count: 2 }],
    ['invalid_reference', 'El tipo de muestra «x» no existe.', { invalid_ids: ['x'] }]
  ])('422 %s de los tipos de muestra del POST: error en la sección de tipos', async (code, message, details) => {
    fake.failures['POST /lab-tests'] = new ApiRequestError({ code, message, details }, 422)
    const { dialog, form } = await mountModal(null)
    await fillBasics(dialog)
    await pickRojo(dialog)
    await submitForm(form)
    expect(section(dialog, 'Tipos de muestra').textContent).toContain(message)
  })

  it('422 inactive_reference de un tipo de muestra: aviso del formulario', async () => {
    fake.failures['POST /lab-tests'] = new ApiRequestError(
      { code: 'inactive_reference', message: 'El tipo de muestra «TRO» está inactivo.', details: { sample_type_id: 'rojo' } },
      422
    )
    const { dialog, form } = await mountModal(null)
    await fillBasics(dialog)
    await pickRojo(dialog)
    await submitForm(form)
    expect(form.textContent).toContain('El tipo de muestra «TRO» está inactivo.')
  })

  it('409 de código duplicado: error en el campo Código y el modal sigue abierto', async () => {
    fake.failures['PATCH /lab-tests/t1'] = new ApiRequestError(
      { code: 'conflict', message: 'Ya existe un examen con el código «GLU».', details: { code: 'GLU' } },
      409
    )
    const { wrapper, dialog, form } = await mountModal(entity())
    await submitForm(form)
    expect(fieldError(dialog, 'Código')).toBe('Ya existe un examen con el código «GLU».')
    expect(wrapper.emitted('saved')).toBeUndefined()
    expect(wrapper.emitted('update:open')).toBeUndefined()
  })

  it('422 inactive_reference del área: error en el campo Área', async () => {
    fake.failures['POST /lab-tests'] = new ApiRequestError(
      { code: 'inactive_reference', message: 'El área «QUI» está inactiva.', details: { area_id: 'a2' } },
      422
    )
    const { dialog, form } = await mountModal(null)
    await fillBasics(dialog)
    await setValue(control<HTMLSelectElement>(dialog, 'Área'), 'a2')
    await pickRojo(dialog)
    await submitForm(form)
    expect(fieldError(dialog, 'Área')).toBe('El área «QUI» está inactiva.')
  })

  // El backend reporta la etiqueta/plantilla inactiva con la clave de la
  // ENTIDAD (`print_label_id` / `result_template_id`), no la de la versión.
  it('422 inactive_reference de la etiqueta: error en la versión de etiqueta (no un aviso suelto)', async () => {
    fake.failures['PATCH /lab-tests/t1'] = new ApiRequestError(
      { code: 'inactive_reference', message: 'La etiqueta «ETQ» está inactiva.', details: { print_label_id: 'pl1' } },
      422
    )
    const { dialog, form } = await mountModal(entity())
    await submitForm(form)
    expect(fieldError(section(dialog, 'Etiqueta de impresión'), 'Versión publicada')).toBe('La etiqueta «ETQ» está inactiva.')
    expect(dialog.querySelector('form [role="alert"]:not(p)')).toBeNull()
  })

  it('422 de versión no publicada: error en la versión de plantilla', async () => {
    fake.failures['PATCH /lab-tests/t1'] = new ApiRequestError(
      {
        code: 'validation_error',
        message: 'La version de plantilla de resultados \'v9\' no existe o no esta publicada.',
        details: { result_template_version_id: 'v9' }
      },
      422
    )
    const { dialog, form } = await mountModal(entity())
    await submitForm(form)
    expect(fieldError(section(dialog, 'Plantilla de resultados'), 'Versión publicada')).toContain('no esta publicada')
  })

  it('422 de schema (FastAPI) se ubica en el campo por el último segmento de loc', async () => {
    fake.failures['PATCH /lab-tests/t1'] = new ApiRequestError(
      { code: 'request_validation', message: 'Algunos datos no son válidos.', details: [{ loc: ['body', 'turnaround_hours'], msg: 'Debe ser ≤ 720.' }] },
      422
    )
    const { dialog, form } = await mountModal(entity())
    await submitForm(form)
    expect(fieldError(dialog, 'Tiempo de entrega (horas)')).toBe('Debe ser ≤ 720.')
  })

  it('un error sin campo va al aviso del formulario', async () => {
    fake.failures['PATCH /lab-tests/t1'] = new ApiRequestError({ code: 'network_error', message: 'No se pudo establecer conexión con el servidor.' })
    const { dialog, form } = await mountModal(entity())
    await submitForm(form)
    expect(form.textContent).toContain('No se pudo establecer conexión con el servidor.')
    expect(button(dialog, 'Guardar cambios')).toBeTruthy()
  })
})
