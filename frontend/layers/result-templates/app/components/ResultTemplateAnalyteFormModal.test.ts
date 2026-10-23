import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiError } from '~/testing/apiError'
import { control, fieldError, flushAll, optionLabels, setValue, submitForm } from '#andromeda/testing/dom'
import type { ResultTemplateVersionContent } from '../composables/useResultTemplateVersionContent'
import type { ResultTemplateAnalyteRead } from '../types/result-templates'
import ResultTemplateAnalyteFormModal from './ResultTemplateAnalyteFormModal.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const BASE = '/result-templates/t1/versions/v1/analytes'

/** Contenido de la versión con lo mínimo que usa el formulario. */
const content = {
  templateId: 't1',
  versionId: 'v1',
  templateAnalytes: [],
  catalogError: null,
  analyteOptionsFor: () => [{ value: 'an1', label: 'LDL (LDL-C)' }],
  sectionOptionsFor: () => [],
  optionSetOptionsFor: () => [{ value: 'os1', label: 'Títulos (titulos)' }],
  unitOptionsFor: () => [],
  analyteDefaultUnitId: () => null,
  formulaCodes: () => ['CHOL', 'HDL-C']
} as unknown as ResultTemplateVersionContent

function entity(over: Partial<ResultTemplateAnalyteRead> = {}): ResultTemplateAnalyteRead {
  return {
    id: 'ta1',
    version_id: 'v1',
    section_id: null,
    analyte_id: 'an1',
    sort_order: 0,
    result_type: 'calculated',
    unit_id: null,
    decimals: 1,
    option_set_id: null,
    formula: '{CHOL} - {HDL-C}',
    default_value: null,
    is_required: true,
    is_reportable: true,
    is_active: true,
    ...over
  } as ResultTemplateAnalyteRead
}

beforeEach(() => {
  fake.reset()
  document.body.innerHTML = ''
})

async function mountModal(lab: ResultTemplateAnalyteRead | null) {
  const wrapper = await mountSuspended(ResultTemplateAnalyteFormModal, {
    props: { entity: lab, content, open: true },
    attachTo: document.body
  })
  await flushAll()
  const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
  return { wrapper, dialog, form: dialog.querySelector('form')! }
}

describe('ResultTemplateAnalyteFormModal: fórmula', () => {
  it('un analito calculado muestra la ayuda de sintaxis y los códigos que se pueden usar', async () => {
    const { dialog } = await mountModal(entity())
    expect(dialog.textContent).toContain('{LDL-C}')
    expect(dialog.textContent).toContain('Códigos que puedes usar: CHOL, HDL-C')
    expect(control(dialog, 'Fórmula').value).toBe('{CHOL} - {HDL-C}')
  })

  it('los demás tipos no muestran el campo fórmula', async () => {
    const { dialog } = await mountModal(entity({ result_type: 'numeric', formula: null }))
    expect(() => control(dialog, 'Fórmula')).toThrow()
  })

  it('422 de la fórmula: un mensaje en español por problema en el campo y el modal sigue abierto', async () => {
    fake.failures[`PATCH ${BASE}/ta1`] = apiError({
      code: 'validation_error',
      message: 'mensaje crudo del backend',
      details: {
        field: 'formula',
        problems: [
          { reason: 'unknown_code', message: 'x', codes: ['ZZ'] },
          { reason: 'cycle', message: 'y', codes: ['LDL-C', 'CHOL', 'LDL-C'] }
        ]
      }
    }, 422)
    const { wrapper, dialog, form } = await mountModal(entity())
    await submitForm(form)

    expect(fieldError(dialog, 'Fórmula')).toBe(
      'Códigos que no son analitos de esta versión: ZZ. Referencia circular: LDL-C → CHOL → LDL-C.'
    )
    expect(wrapper.emitted('saved')).toBeUndefined()
    expect(wrapper.emitted('update:open')).toBeUndefined()
  })

  it('guarda la fórmula en el PATCH', async () => {
    const { wrapper, dialog, form } = await mountModal(entity())
    await setValue(control(dialog, 'Fórmula'), 'CHOL / 2')
    await submitForm(form)
    expect(fake.bodies('PATCH', `${BASE}/ta1`)).toMatchObject([{ formula: 'CHOL / 2', result_type: 'calculated' }])
    expect(wrapper.emitted('saved')).toHaveLength(1)
  })
})

describe('ResultTemplateAnalyteFormModal: título (dilución)', () => {
  it('ofrece el tipo "Título (dilución)" y pide el conjunto de opciones', async () => {
    const { dialog, form } = await mountModal(entity({ result_type: 'numeric', formula: null }))
    expect(optionLabels(control<HTMLSelectElement>(dialog, 'Tipo de resultado'))).toContain('Título (dilución)')

    await setValue(control<HTMLSelectElement>(dialog, 'Tipo de resultado'), 'titer')
    const set = control<HTMLSelectElement>(dialog, 'Conjunto de opciones')
    expect(optionLabels(set)).toContain('Títulos (titulos)')
    await setValue(set, 'os1')
    await submitForm(form)
    expect(fake.bodies('PATCH', `${BASE}/ta1`)).toMatchObject([{ result_type: 'titer', option_set_id: 'os1', unit_id: null, decimals: null }])
  })
})
