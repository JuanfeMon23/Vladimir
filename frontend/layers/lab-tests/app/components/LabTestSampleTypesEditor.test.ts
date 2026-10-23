import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiError } from '~/testing/apiError'
import { fakePage } from '~/testing/fakeApi'
import { ALL_LAB_TESTS_TAGS, LAB_TEST_SELECTOR_VIEW_TAGS } from '~/testing/session'
import { signInWith } from '#leo-client/testing/session'
import { control, flushAll, hasRow, isShown, rowOf, setChecked, setValue, submitForm } from '#andromeda/testing/dom'
import LabTestSampleTypesEditor from './LabTestSampleTypesEditor.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const SUERO = 'Suero (SUE · Sangre)'
const PLASMA = 'Plasma (PLA · Sangre)'
const EDTA = 'EDTA viejo (EDT · Sangre)'
const ORINA = 'Orina (ORI · Orina)'

beforeEach(() => {
  signInWith([...ALL_LAB_TESTS_TAGS, ...LAB_TEST_SELECTOR_VIEW_TAGS])
  fake.reset()
  document.body.innerHTML = ''
  fake.routes['GET /samples'] = fakePage([
    {
      id: 's1',
      code: 'SAN',
      name: 'Sangre',
      is_active: true,
      types: [
        { id: 'suero', code: 'SUE', name: 'Suero', specimen: 'serum', is_active: true },
        { id: 'plasma', code: 'PLA', name: 'Plasma', specimen: 'plasma', is_active: true },
        { id: 'edta', code: 'EDT', name: 'EDTA viejo', specimen: 'blood', is_active: false }
      ]
    },
    // Muestra inactiva: sus tipos no se ofrecen aunque estén activos.
    { id: 's2', code: 'ORI', name: 'Orina', is_active: false, types: [{ id: 'orina', code: 'ORI', name: 'Orina', specimen: 'urine', is_active: true }] }
  ])
  fake.routes['GET /lab-tests/t1/sample-types'] = [
    // Vigente y preferida, aunque el tipo ya está desactivado: se conserva.
    { id: 'L-edta', sample_type_id: 'edta', is_preferred: true, required_volume_ml: 2, sort_order: 1, is_active: true },
    // Quitada antes: el tipo sigue activo y se ofrece de nuevo.
    { id: 'L-plasma', sample_type_id: 'plasma', is_preferred: false, required_volume_ml: null, sort_order: 2, is_active: false }
  ]
})

async function mountEditor() {
  const wrapper = await mountSuspended(LabTestSampleTypesEditor, { props: { labTestId: 't1' }, attachTo: document.body })
  await flushAll()
  const root = wrapper.element.parentElement as HTMLElement
  return { root, form: root.querySelector('form')! }
}

describe('LabTestSampleTypesEditor', () => {
  it('carga con include_inactive y conserva el tipo asignado aunque esté inactivo', async () => {
    const { root } = await mountEditor()
    expect(fake.requests).toHaveBeenCalledWith('GET', '/lab-tests/t1/sample-types', { params: { include_inactive: true } })

    const edta = rowOf(root, EDTA)
    expect(control(edta, EDTA).checked).toBe(true)
    expect(edta.textContent).toContain('Inactivo')
    expect(control(edta, 'Preferido').checked).toBe(true)
    expect(control(edta, 'Volumen (mL)').value).toBe('2')
  })

  it('el catálogo para agregar solo ofrece tipos activos de muestras activas', async () => {
    const { root } = await mountEditor()
    expect(hasRow(root, SUERO)).toBe(true)
    expect(hasRow(root, PLASMA)).toBe(true)
    expect(hasRow(root, ORINA)).toBe(false)
  })

  it('"Mostrar inactivos" marca la asignación quitada', async () => {
    const { root } = await mountEditor()
    expect(rowOf(root, PLASMA).textContent).not.toContain('Asignación quitada')
    await setChecked(root, 'Mostrar inactivos', true)
    expect(rowOf(root, PLASMA).textContent).toContain('Asignación quitada')
  })

  it('agregar un tipo y marcarlo preferido desmarca el otro y el PUT envía el set completo', async () => {
    const { root, form } = await mountEditor()
    await setChecked(root, SUERO, true)
    const suero = rowOf(root, SUERO)
    expect(isShown(control(suero, 'Preferido'))).toBe(true)
    await setChecked(suero, 'Preferido', true)
    await setValue(control(suero, 'Volumen (mL)'), '3.5')

    expect(control(rowOf(root, EDTA), 'Preferido').checked).toBe(false)

    await submitForm(form)
    expect(fake.bodies('PUT', '/lab-tests/t1/sample-types')).toEqual([[
      { sample_type_id: 'edta', is_preferred: false, required_volume_ml: 2, sort_order: 1 },
      { sample_type_id: 'suero', is_preferred: true, required_volume_ml: 3.5, sort_order: 2 }
    ]])
    expect(root.textContent).toContain('Tipos de muestra guardados.')
  })

  it('desmarcar un tipo lo quita del PUT y reinicia su fila', async () => {
    const { root, form } = await mountEditor()
    await setChecked(root, SUERO, true)
    const suero = rowOf(root, SUERO)
    await setChecked(suero, 'Preferido', true)
    await setChecked(root, EDTA, false)
    expect(isShown(control(rowOf(root, EDTA), 'Preferido'))).toBe(false)

    await submitForm(form)
    expect(fake.bodies('PUT', '/lab-tests/t1/sample-types')).toEqual([[
      { sample_type_id: 'suero', is_preferred: true, required_volume_ml: null, sort_order: 1 }
    ]])

    // Al volver a marcarlo, la fila arranca vacía.
    await setChecked(root, EDTA, true)
    expect(control(rowOf(root, EDTA), 'Preferido').checked).toBe(false)
    expect(control(rowOf(root, EDTA), 'Volumen (mL)').value).toBe('')
  })

  it('con tipos asignados y ninguno preferido no envía y avisa en el formulario', async () => {
    const { root, form } = await mountEditor()
    await setChecked(rowOf(root, EDTA), 'Preferido', false)
    await setChecked(root, SUERO, true)
    await submitForm(form)
    expect(fake.bodies('PUT', '/lab-tests/t1/sample-types')).toEqual([])
    expect(form.querySelector('[role="alert"]')?.textContent).toContain('Marca exactamente un tipo de muestra como preferido.')

    // Al corregirlo, envía y el aviso desaparece.
    await setChecked(rowOf(root, SUERO), 'Preferido', true)
    await submitForm(form)
    expect(fake.bodies('PUT', '/lab-tests/t1/sample-types')).toHaveLength(1)
    expect(form.textContent).not.toContain('Marca exactamente un tipo de muestra como preferido.')
  })

  it('no deja quitar el último tipo: sin PUT vacío y con mensaje claro', async () => {
    const { root, form } = await mountEditor()
    await setChecked(root, EDTA, false)
    await submitForm(form)
    expect(fake.bodies('PUT', '/lab-tests/t1/sample-types')).toEqual([])
    expect(form.querySelector('[role="alert"]')?.textContent).toContain('El examen debe tener al menos un tipo de muestra.')
    expect(root.textContent).not.toContain('Tipos de muestra guardados.')

    // Al marcar otro como preferido, ya envía y el aviso desaparece.
    await setChecked(root, SUERO, true)
    await setChecked(rowOf(root, SUERO), 'Preferido', true)
    await submitForm(form)
    expect(fake.bodies('PUT', '/lab-tests/t1/sample-types')).toHaveLength(1)
    expect(form.textContent).not.toContain('El examen debe tener al menos un tipo de muestra.')
  })

  it('el 422 de conteo de preferidos del backend se muestra en el aviso del formulario', async () => {
    fake.failures['PUT /lab-tests/t1/sample-types'] = apiError(
      {
        code: 'validation_error',
        message: 'Debe haber exactamente un tipo de muestra con \'is_preferred=true\' (se recibieron 0).',
        details: { preferred_count: 0 }
      },
      422
    )
    const { root, form } = await mountEditor()
    await submitForm(form)

    expect(fake.bodies('PUT', '/lab-tests/t1/sample-types')).toHaveLength(1)
    const alert = form.querySelector('[role="alert"]')
    expect(alert?.textContent).toContain('Debe haber exactamente un tipo de muestra')
    expect(root.textContent).not.toContain('Tipos de muestra guardados.')
  })

  it('el 422 inactive_reference (tipo desactivado entretanto) se muestra en el aviso', async () => {
    fake.failures['PUT /lab-tests/t1/sample-types'] = apiError(
      { code: 'inactive_reference', message: 'El tipo de muestra «SUE» está inactivo.', details: { sample_type_id: 'suero' } },
      422
    )
    const { root, form } = await mountEditor()
    await setChecked(root, SUERO, true)
    await submitForm(form)
    expect(form.querySelector('[role="alert"]')?.textContent).toContain('El tipo de muestra «SUE» está inactivo.')
  })

  it('volumen negativo no envía y marca el campo', async () => {
    const { root, form } = await mountEditor()
    await setValue(control(rowOf(root, EDTA), 'Volumen (mL)'), '-1')
    await submitForm(form)
    expect(fake.bodies('PUT', '/lab-tests/t1/sample-types')).toEqual([])
    expect(rowOf(root, EDTA).textContent).toContain('Debe ser mayor o igual a 0.')
  })
})
