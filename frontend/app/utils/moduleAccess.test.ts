import { describe, expect, it } from 'vitest'
import { MODULE_VIEW, noViewMessage } from './moduleAccess'

describe('moduleAccess', () => {
  it('cada módulo apunta a su tag view de Vladimir', () => {
    expect(MODULE_VIEW.labAreas.tag).toBe('vladimir.lab-areas.view')
    expect(MODULE_VIEW.printLabels.tag).toBe('vladimir.print-labels.view')
    expect(MODULE_VIEW.resultTemplates.tag).toBe('vladimir.result-templates.view')
    expect(MODULE_VIEW.preconditions.tag).toBe('vladimir.preconditions.view')
    expect(MODULE_VIEW.samples.tag).toBe('vladimir.samples.view')
    expect(MODULE_VIEW.consentDocuments.tag).toBe('vladimir.consent-documents.view')
  })

  it('el aviso nombra el módulo', () => {
    expect(noViewMessage(MODULE_VIEW.samples)).toBe('No tienes permiso para consultar muestras.')
  })
})
