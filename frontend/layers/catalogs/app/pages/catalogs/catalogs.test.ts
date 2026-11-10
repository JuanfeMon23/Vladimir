import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import DefaultLayout from '~/layouts/default.vue'
import { apiError } from '~/testing/apiError'
import { CATALOG_FIXTURES, fakeCatalogs } from '~/testing/catalogs'
import { ALL_CATALOGS_TAGS } from '~/testing/session'
import { signInWith } from '#leo-client/testing/session'
import { button, click, control, fieldError, flushAll, optionLabels, setChecked, setValue, submitForm } from '#andromeda/testing/dom'
import CatalogsPage from './index.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const VIEW = 'vladimir.catalogs.view'
const CREATE = 'vladimir.catalogs.create'
const EDIT = 'vladimir.catalogs.edit'
const STATUS = 'vladimir.catalogs.change-status'

beforeEach(() => {
  fake.reset()
  fakeCatalogs(fake)
  document.body.innerHTML = ''
})

async function mountPage(tags: string[], catalog?: string) {
  signInWith(tags)
  const wrapper = await mountSuspended(CatalogsPage, { route: catalog ? `/catalogs?catalog=${catalog}` : '/catalogs', attachTo: document.body })
  await flushAll()
  return wrapper
}

const cells = (root: ParentNode) => [...root.querySelectorAll('tr.group')].map(row => [...row.querySelectorAll('td')].map(cell => cell.textContent?.trim()))
const headers = (root: ParentNode) => [...root.querySelectorAll('thead th')].map(header => header.textContent?.trim())

async function openFirstRow(wrapper: Awaited<ReturnType<typeof mountPage>>) {
  await wrapper.find('tr.group button').trigger('click')
  await flushAll()
  const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
  return { dialog, form: dialog.querySelector('form')! }
}

describe('permisos y navegación de catálogos', () => {
  it('la pantalla exige catalogs.view', () => {
    const meta = (useRouter().resolve('/catalogs').meta as { leo?: { tag?: string } }).leo?.tag
    expect(meta).toBe(VIEW)
  })

  it('el ítem «Catálogos» del menú aparece con view y no sin él', async () => {
    signInWith([VIEW])
    expect((await mountSuspended(DefaultLayout)).findAll('nav a').map(link => link.text())).toEqual(['Catálogos'])
    signInWith([CREATE, EDIT, STATUS])
    expect((await mountSuspended(DefaultLayout)).findAll('nav a').map(link => link.text())).toEqual([])
  })

  it('«Nuevo …» exige create; la acción de fila es «Ver» sin edit ni change-status y «Ver / Editar» con alguno', async () => {
    expect((await mountPage([VIEW])).text()).not.toContain('Nuevo tipo de documento')
    const withCreate = await mountPage([VIEW, CREATE])
    expect(withCreate.text()).toContain('Nuevo tipo de documento')
    expect(withCreate.find('tr.group button').text()).toBe('Ver')
    expect((await mountPage([VIEW, STATUS])).find('tr.group button').text()).toBe('Ver / Editar')
  })
})

describe('listado y selector', () => {
  it('ofrece los 9 catálogos y lista el primero con todos sus valores', async () => {
    const wrapper = await mountPage([VIEW])
    expect(optionLabels(control<HTMLSelectElement>(wrapper.element as HTMLElement, 'Catálogo'))).toEqual([
      'Tipos de documento a firmar', 'Firmantes', 'Unidades de duración', 'Tipos de precondición', 'Categorías de precondición',
      'Especímenes', 'Tipos de resultado', 'Sexos', 'Unidades de edad'
    ])
    expect(fake.requests).toHaveBeenCalledWith('GET', '/catalogs/consent-document-types', expect.objectContaining({ params: { include_inactive: true } }))
    expect(headers(wrapper.element)).toEqual(['Código', 'Nombre', 'Orden', 'Estado', ''])
    expect(cells(wrapper.element).map(row => row[0])).toEqual(['consentimiento_informado', 'tratamiento_datos', 'otro'])
  })

  it('cada catálogo muestra sus columnas de comportamiento', async () => {
    const resultTypes = await mountPage([VIEW], 'result-types')
    expect(headers(resultTypes.element)).toEqual([
      'Código', 'Nombre', 'Orden', 'Usa conjunto de opciones', 'Rango numérico', 'Rango booleano', 'Usa unidad y decimales',
      'Usa fórmula', 'Exige rango de referencia', 'Estado', ''
    ])
    const calculated = cells(resultTypes.element).find(row => row[0] === 'calculated')!
    expect(calculated.slice(3, 9)).toEqual(['No', 'Sí', 'No', 'Sí', 'Sí', 'Sí'])

    expect(headers((await mountPage([VIEW], 'sexes')).element)).toContain('Comodín («cualquiera»)')
    expect(headers((await mountPage([VIEW], 'age-units')).element)).toContain('Días por unidad')
    expect(headers((await mountPage([VIEW], 'duration-units')).element)).toContain('Minutos por unidad')
    const ageUnits = cells((await mountPage([VIEW], 'age-units')).element)
    expect(ageUnits.map(row => row[3])).toEqual(['1', '30.4375', '365.25'])
  })

  it('cambiar el catálogo del selector recarga su listado', async () => {
    const wrapper = await mountPage([VIEW])
    await setValue(control<HTMLSelectElement>(wrapper.element as HTMLElement, 'Catálogo'), 'consent-signers')
    await flushAll()
    expect(cells(wrapper.element).map(row => row[0])).toEqual(['paciente', 'paciente_o_representante'])
  })

  it('el filtro de estado separa activos e inactivos', async () => {
    fake.routes['GET /catalogs/consent-signers'] = [
      ...CATALOG_FIXTURES['consent-signers'],
      { id: 'v', code: 'viejo', name: 'Viejo', sort_order: 9, is_active: false, created_at: '', updated_at: '' }
    ]
    const wrapper = await mountPage([VIEW], 'consent-signers')
    expect(cells(wrapper.element)).toHaveLength(3)
    await setValue(control<HTMLSelectElement>(wrapper.element as HTMLElement, 'Estado'), 'inactive')
    await flushAll()
    expect(cells(wrapper.element).map(row => row[0])).toEqual(['viejo'])
  })

  it('un fallo de carga se muestra legible', async () => {
    fake.failures['GET /catalogs/consent-document-types'] = apiError({ code: 'internal_error', message: 'x' }, 500)
    const wrapper = await mountPage([VIEW])
    expect(wrapper.text()).toContain('error en el servidor')
  })
})

describe('crear', () => {
  it('un catálogo simple envía código, nombre y orden sugerido (siguiente al mayor)', async () => {
    const wrapper = await mountPage([VIEW, CREATE], 'consent-signers')
    await click(button(wrapper.element as HTMLElement, 'Nuevo firmante'))
    const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
    expect(control<HTMLInputElement>(dialog, 'Orden').value).toBe('2')
    expect(control<HTMLInputElement>(dialog, 'Código').disabled).toBe(false)
    await setValue(control(dialog, 'Código'), 'tutor')
    await setValue(control(dialog, 'Nombre'), 'Tutor legal')
    await submitForm(dialog.querySelector('form')!)
    expect(fake.bodies('POST', '/catalogs/consent-signers')).toEqual([
      { code: 'tutor', name: 'Tutor legal', sort_order: 2, is_active: true }
    ])
  })

  it('un tipo de resultado envía sus banderas', async () => {
    await mountPage([VIEW, CREATE], 'result-types')
    await click(button(document.body, 'Nuevo tipo de resultado'))
    const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
    await setValue(control(dialog, 'Código'), 'molecular')
    await setValue(control(dialog, 'Nombre'), 'Molecular')
    await setChecked(dialog, 'Usa fórmula', true)
    await setChecked(dialog, 'Usa unidad y decimales', true)
    await submitForm(dialog.querySelector('form')!)
    expect(fake.bodies('POST', '/catalogs/result-types')[0]).toMatchObject({
      code: 'molecular', uses_formula: true, uses_unit: true, uses_option_set: false, uses_numeric_range: false,
      uses_boolean_range: false, requires_reference_range: false
    })
  })

  it('las columnas numéricas son obligatorias y positivas', async () => {
    await mountPage([VIEW, CREATE], 'age-units')
    await click(button(document.body, 'Nueva unidad de edad'))
    const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
    await setValue(control(dialog, 'Código'), 'semanas')
    await setValue(control(dialog, 'Nombre'), 'Semanas')
    await submitForm(dialog.querySelector('form')!)
    expect(fieldError(dialog, 'Días por unidad')).toBe('Días por unidad: es obligatorio.')
    await setValue(control(dialog, 'Días por unidad'), '0')
    await submitForm(dialog.querySelector('form')!)
    expect(fieldError(dialog, 'Días por unidad')).toBe('Días por unidad: debe ser mayor que 0.')
    expect(fake.bodies('POST', '/catalogs/age-units')).toEqual([])
    await setValue(control(dialog, 'Días por unidad'), '7')
    await submitForm(dialog.querySelector('form')!)
    expect(fake.bodies('POST', '/catalogs/age-units')[0]).toMatchObject({ code: 'semanas', days: 7 })
  })

  it('el 409 de código duplicado se muestra en Código', async () => {
    fake.failures['POST /catalogs/consent-signers'] = apiError(
      { code: 'conflict', message: 'Ya existe un firmante con el código tutor.', details: { code: 'tutor' } }, 409
    )
    await mountPage([VIEW, CREATE], 'consent-signers')
    await click(button(document.body, 'Nuevo firmante'))
    const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
    await setValue(control(dialog, 'Código'), 'tutor')
    await setValue(control(dialog, 'Nombre'), 'Tutor')
    await submitForm(dialog.querySelector('form')!)
    expect(fieldError(dialog, 'Código')).toBe('Ya existe un firmante con el código tutor.')
  })

  it('el 409 de un segundo sexo comodín se muestra en la casilla Comodín, no en Código', async () => {
    const message = 'Ya existe un sexo comodín (any); solo puede haber uno.'
    fake.failures['POST /catalogs/sexes'] = apiError({ code: 'conflict', message, details: { code: 'any', id: 'any-id' } }, 409)
    await mountPage([VIEW, CREATE], 'sexes')
    await click(button(document.body, 'Nuevo sexo'))
    const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
    await setValue(control(dialog, 'Código'), 'todos')
    await setValue(control(dialog, 'Nombre'), 'Todos')
    await setChecked(dialog, 'Comodín («cualquiera»)', true)
    await submitForm(dialog.querySelector('form')!)
    expect(fieldError(dialog, 'Código')).toBeNull()
    expect(dialog.textContent).toContain(message)
  })
})

describe('editar y activar o desactivar', () => {
  it('el código no se edita y el PATCH no lo envía', async () => {
    const wrapper = await mountPage([VIEW, EDIT], 'consent-signers')
    const { dialog, form } = await openFirstRow(wrapper)
    expect(control<HTMLInputElement>(dialog, 'Código').disabled).toBe(true)
    await setValue(control(dialog, 'Nombre'), 'Paciente (titular)')
    await submitForm(form)
    expect(fake.bodies('PATCH', '/catalogs/consent-signers/paciente-id')).toEqual([
      { name: 'Paciente (titular)', sort_order: 0 }
    ])
  })

  it('desactivar envía is_active y el motivo (change-status) sin datos si no hay edit', async () => {
    const wrapper = await mountPage([VIEW, STATUS], 'consent-signers')
    const { dialog, form } = await openFirstRow(wrapper)
    expect(control<HTMLInputElement>(dialog, 'Nombre').disabled).toBe(true)
    await setChecked(dialog, 'Activo', false)
    await setValue(control(dialog, 'Motivo de la desactivación'), 'Ya no se usa')
    await submitForm(form)
    expect(fake.bodies('PATCH', '/catalogs/consent-signers/paciente-id')).toEqual([
      { is_active: false, activity_reason: 'Ya no se usa' }
    ])
  })

  it('con solo view el modal es de lectura', async () => {
    const wrapper = await mountPage([VIEW], 'consent-signers')
    const { dialog } = await openFirstRow(wrapper)
    expect(dialog.textContent).not.toContain('Guardar cambios')
    expect(dialog.textContent).not.toContain('Activo')
    expect(control<HTMLInputElement>(dialog, 'Nombre').disabled).toBe(true)
  })

  it('cambiar una bandera de un tipo de resultado viaja en el PATCH', async () => {
    const wrapper = await mountPage([VIEW, EDIT], 'result-types')
    const { dialog, form } = await openFirstRow(wrapper)
    expect(control<HTMLInputElement>(dialog, 'Rango numérico').checked).toBe(true)
    await setChecked(dialog, 'Rango numérico', false)
    await submitForm(form)
    expect(fake.bodies('PATCH', '/catalogs/result-types/numeric-id')[0]).toMatchObject({ uses_numeric_range: false, uses_unit: true })
  })
})
