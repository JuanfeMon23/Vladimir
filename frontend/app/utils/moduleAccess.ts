/**
 * Tag `view` de cada módulo que otro consulta para llenar un selector
 * (p. ej. el formulario de examen lista áreas, etiquetas, plantillas…). Viven
 * en el núcleo para que una layer no importe de otra; cada layer define los
 * suyos completos en su propio archivo de tags.
 */
export interface ModuleView {
  tag: string
  /** Nombre del módulo en minúsculas, para "consultar <módulo>". */
  label: string
}

export const MODULE_VIEW = {
  labAreas: { tag: 'vladimir.lab-areas.view', label: 'áreas' },
  printLabels: { tag: 'vladimir.print-labels.view', label: 'etiquetas de impresión' },
  resultTemplates: { tag: 'vladimir.result-templates.view', label: 'plantillas de resultados' },
  preconditions: { tag: 'vladimir.preconditions.view', label: 'precondiciones' },
  samples: { tag: 'vladimir.samples.view', label: 'muestras' },
  consentDocuments: { tag: 'vladimir.consent-documents.view', label: 'documentos a firmar' }
} as const satisfies Record<string, ModuleView>

/** Aviso cuando falta el `view` de un módulo del que depende un selector. */
export function noViewMessage(module: ModuleView): string {
  return `No tienes permiso para consultar ${module.label}.`
}
