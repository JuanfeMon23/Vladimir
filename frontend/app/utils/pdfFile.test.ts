import { describe, expect, it } from 'vitest'
import {
  PDF_MAX_BYTES,
  base64ToBlob,
  fileToBase64,
  formatFileSize,
  pdfFileErrorMessage,
  shortSha,
  validatePdfFile
} from './pdfFile'

const PDF_BYTES = new TextEncoder().encode('%PDF-1.4\n%âã\n1 0 obj\n<<>>\nendobj\n%%EOF')

function pdf(overrides: Partial<{ name: string, type: string, size: number }> = {}) {
  return { name: 'consentimiento.pdf', type: 'application/pdf', size: 1024, ...overrides }
}

describe('validatePdfFile', () => {
  it('acepta un PDF normal', () => {
    expect(validatePdfFile(pdf())).toBeNull()
  })

  it('acepta el tipo vacío si la extensión es .pdf (algunos navegadores no lo informan)', () => {
    expect(validatePdfFile(pdf({ type: '' }))).toBeNull()
  })

  it('acepta la extensión en mayúsculas', () => {
    expect(validatePdfFile(pdf({ name: 'DOC.PDF' }))).toBeNull()
  })

  it('rechaza un tipo que no es PDF', () => {
    expect(validatePdfFile(pdf({ type: 'image/png' }))).toBe('not_pdf')
  })

  it('rechaza una extensión que no es .pdf aunque el tipo sea PDF', () => {
    expect(validatePdfFile(pdf({ name: 'doc.txt' }))).toBe('not_pdf')
    expect(validatePdfFile(pdf({ name: 'sin-extension' }))).toBe('not_pdf')
  })

  it('rechaza un archivo vacío', () => {
    expect(validatePdfFile(pdf({ size: 0 }))).toBe('empty')
  })

  it('acepta exactamente 5 MB y rechaza un byte más', () => {
    expect(validatePdfFile(pdf({ size: PDF_MAX_BYTES }))).toBeNull()
    expect(validatePdfFile(pdf({ size: PDF_MAX_BYTES + 1 }))).toBe('too_large')
  })

  it('prioriza el tipo incorrecto sobre el tamaño', () => {
    expect(validatePdfFile(pdf({ name: 'a.txt', size: 0 }))).toBe('not_pdf')
  })
})

describe('pdfFileErrorMessage', () => {
  it.each([
    ['empty', 'El archivo está vacío.'],
    ['too_large', 'El archivo supera los 5 MB.'],
    ['invalid_base64', 'El archivo no se pudo leer correctamente.'],
    ['not_pdf', 'El archivo no es un PDF válido.']
  ])('traduce %s', (reason, message) => {
    expect(pdfFileErrorMessage(reason)).toBe(message)
  })

  it('usa el texto de respaldo con un reason desconocido o ausente', () => {
    expect(pdfFileErrorMessage('otra', 'Falló.')).toBe('Falló.')
    expect(pdfFileErrorMessage(undefined)).toBe('No se pudo procesar el archivo.')
  })
})

describe('fileToBase64 / base64ToBlob', () => {
  it('devuelve base64 puro, sin prefijo data:', async () => {
    const base64 = await fileToBase64(new Blob([PDF_BYTES], { type: 'application/pdf' }))
    expect(base64.startsWith('data:')).toBe(false)
    expect(base64).toMatch(/^[A-Za-z0-9+/]+={0,2}$/)
    expect(atob(base64).startsWith('%PDF-')).toBe(true)
  })

  it('es reversible: los bytes del Blob son íntegros', async () => {
    const base64 = await fileToBase64(new Blob([PDF_BYTES]))
    const blob = base64ToBlob(base64, 'application/pdf')
    expect(blob.type).toBe('application/pdf')
    expect(blob.size).toBe(PDF_BYTES.length)
    expect(new Uint8Array(await blob.arrayBuffer())).toEqual(PDF_BYTES)
  })

  it('maneja archivos más grandes que un bloque de conversión', async () => {
    const big = new Uint8Array(300_000).map((_, i) => i % 251)
    const blob = base64ToBlob(await fileToBase64(new Blob([big])), 'application/pdf')
    expect(new Uint8Array(await blob.arrayBuffer())).toEqual(big)
  })
})

describe('formatFileSize', () => {
  it.each([
    [0, '0 B'],
    [512, '512 B'],
    [1024, '1 KB'],
    [1536, '1,5 KB'],
    [1024 * 1024, '1 MB'],
    [Math.round(2.3 * 1024 * 1024), '2,3 MB'],
    [5 * 1024 * 1024, '5 MB']
  ])('%i bytes -> %s', (bytes, text) => {
    expect(formatFileSize(bytes)).toBe(text)
  })
})

describe('shortSha', () => {
  const sha = 'a'.repeat(8) + 'b'.repeat(8) + 'c'.repeat(48)

  it('recorta a 12 caracteres con elipsis', () => {
    expect(shortSha(sha)).toBe('aaaaaaaabbbb…')
  })

  it('respeta la longitud pedida y no recorta lo que ya cabe', () => {
    expect(shortSha(sha, 4)).toBe('aaaa…')
    expect(shortSha('abc')).toBe('abc')
  })
})
