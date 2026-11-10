import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiError } from '~/testing/apiError'
import { CATALOG_FIXTURES, catalogContentStub } from '~/testing/catalogs'
import { fakePage } from '~/testing/fakeApi'
import { control, fieldError, flushAll, optionLabels, setValue, submitForm } from '#andromeda/testing/dom'
import type { ResultTemplateVersionContent } from '../composables/useResultTemplateVersionContent'
import type { ReferenceRangeRead, ResultTemplateAnalyteRead } from '../types/result-templates'
import ResultTemplateReferenceRangeFormModal from './ResultTemplateReferenceRangeFormModal.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const RANGES = '/result-templates/t1/versions/v1/analytes/ta1/reference-ranges'

function content(fixtures: Parameters<typeof catalogContentStub>[0] = {}) {
  return {
    templateId: 't1',
    versionId: 'v1',
    analyteName: () => 'Glucosa (GLU)',
    ...catalogContentStub(fixtures)
  } as unknown as ResultTemplateVersionContent
}

function analyte(resultType: string): ResultTemplateAnalyteRead {
  return { id: 'ta1', version_id: 'v1', analyte_id: 'an1', result_type: resultType, option_set_id: 'os1', is_active: true } as ResultTemplateAnalyteRead
}

const RANGE = {
  id: 'r1', template_analyte_id: 'ta1', sex: 'male', age_min: 18, age_max: 65, age_unit: 'anos', condition: null,
  low: 70, high: 110, critical_low: null, critical_high: null, expected_option_id: null, expected_boolean: null,
  display_text: null, interpretation: null, is_active: true, created_at: '', updated_at: ''
} satisfies ReferenceRangeRead

beforeEach(() => {
  fake.reset()
  document.body.innerHTML = ''
  fake.routes['GET /result-option-sets/os1/options'] = fakePage([])
})

async function mountModal(resultType: string, entity: ReferenceRangeRead | null = null, versionContent = content()) {
  await mountSuspended(ResultTemplateReferenceRangeFormModal, {
    props: { open: true, entity, templateAnalyte: analyte(resultType), content: versionContent },
    attachTo: document.body
  })
  await flushAll()
  const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
  return { dialog, form: dialog.querySelector('form')! }
}

const hasField = (dialog: HTMLElement, label: string) => {
  try {
    control(dialog, label)
    return true
  } catch {
    return false
  }
}

describe('ResultTemplateReferenceRangeFormModal: catálogos', () => {
  it('sexo y unidad de edad salen de la API y el sexo comodín es el valor inicial', async () => {
    const { dialog } = await mountModal('numeric')
    expect(optionLabels(control<HTMLSelectElement>(dialog, 'Sexo'))).toEqual(['Seleccionar sexo', 'Cualquiera', 'Masculino', 'Femenino'])
    expect(control<HTMLSelectElement>(dialog, 'Sexo').value).toBe('any')
    expect(optionLabels(control<HTMLSelectElement>(dialog, 'Unidad de edad'))).toEqual(['Sin unidad', 'Días', 'Meses', 'Años'])
  })

  it('el comodín inicial es la fila marcada is_wildcard, no un código fijo', async () => {
    const sexes = CATALOG_FIXTURES.sexes.map(sex => ({ ...sex, is_wildcard: sex.code === 'male' }))
    const { dialog } = await mountModal('numeric', null, content({ sexes }))
    expect(control<HTMLSelectElement>(dialog, 'Sexo').value).toBe('male')
  })

  it('los campos tipados salen de las banderas del tipo de resultado', async () => {
    const numeric = await mountModal('numeric')
    expect(hasField(numeric.dialog, 'Mínimo')).toBe(true)
    expect(hasField(numeric.dialog, 'Opción esperada')).toBe(false)
    document.body.innerHTML = ''

    const boolean = await mountModal('boolean')
    expect(hasField(boolean.dialog, 'Booleano esperado')).toBe(true)
    expect(hasField(boolean.dialog, 'Mínimo')).toBe(false)
    document.body.innerHTML = ''

    const text = await mountModal('text')
    expect(hasField(text.dialog, 'Mínimo')).toBe(false)
    expect(hasField(text.dialog, 'Booleano esperado')).toBe(false)
    expect(hasField(text.dialog, 'Opción esperada')).toBe(false)
  })

  it('un tipo nuevo con banderas propias admite sus campos sin tocar el código', async () => {
    const molecular = {
      ...CATALOG_FIXTURES['result-types'][0]!, id: 'mol', code: 'molecular', name: 'Molecular',
      uses_numeric_range: false, uses_boolean_range: true, uses_option_set: true
    }
    const versionContent = content({ 'result-types': [...CATALOG_FIXTURES['result-types'], molecular] })
    const { dialog } = await mountModal('molecular', null, versionContent)
    expect(hasField(dialog, 'Booleano esperado')).toBe(true)
    expect(hasField(dialog, 'Opción esperada')).toBe(true)
    expect(hasField(dialog, 'Mínimo')).toBe(false)
  })

  it('un campo tipado que el tipo no admite no viaja en el PATCH', async () => {
    const { dialog, form } = await mountModal('text', { ...RANGE, low: 1, high: 2 })
    await setValue(control(dialog, 'Texto a mostrar'), 'Negativo')
    await submitForm(form)
    const [body] = fake.bodies('PATCH', `${RANGES}/r1`) as Record<string, unknown>[]
    expect(body).toMatchObject({ sex: 'male', display_text: 'Negativo' })
    expect(body).not.toHaveProperty('low')
  })

  it.each([
    ['sex', 'Sexo', 'invalid_reference', 'El sexo «x» no existe.'],
    ['age_unit', 'Unidad de edad', 'inactive_reference', 'La unidad de edad «anos» está inactiva.']
  ])('el 422 en %s se muestra en el campo %s', async (field, label, code, message) => {
    fake.failures[`PATCH ${RANGES}/r1`] = apiError({ code, message, details: { [field]: 'x' } }, 422)
    const { dialog, form } = await mountModal('numeric', RANGE)
    await submitForm(form)
    expect(fieldError(dialog, label)).toBe(message)
  })
})
