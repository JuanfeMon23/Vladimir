import { z } from 'zod'

/**
 * Constructores de campos zod repetidos en los formularios de las layers
 * (texto obligatorio con longitud máxima, texto/correo/número opcional que
 * viaja como `null` cuando está vacío, enum desde un `<UiSelect>`). Los
 * mensajes van en español; el `requiredMessage` se pasa completo para
 * respetar la concordancia ("El código es obligatorio." / "La categoría es
 * obligatoria.").
 *
 * La salida ya es el payload del backend: opcionales vacíos → `null`,
 * números como `number`.
 */

const maxMessage = (max: number) => `Máximo ${max} caracteres.`

/** Texto obligatorio, recortado, con longitud máxima (sin `max` no limita: columnas `Text`). */
export function zRequiredText(requiredMessage: string, max?: number) {
  const base = z
    .string({ required_error: requiredMessage, invalid_type_error: requiredMessage })
    .trim()
    .min(1, requiredMessage)
  return max === undefined ? base : base.max(max, maxMessage(max))
}

/** Texto opcional: `''`/espacios/`null` → `null`. Sin `max` no limita la longitud (columnas `Text`). */
export function zOptionalText(max?: number) {
  const base = z.string().trim()
  const limited = max === undefined ? base : base.max(max, maxMessage(max))
  return z
    .union([limited, z.null()])
    .optional()
    .transform(value => (value ? value : null))
}

/** Correo opcional: vacío → `null`; si hay texto, debe ser un correo válido. */
export function zOptionalEmail(max = 255) {
  return z
    .union([
      z.literal(''),
      z.null(),
      z.string().trim().max(max, maxMessage(max)).email('Ingresa un correo electrónico válido.')
    ])
    .optional()
    .transform(value => (value ? value : null))
}

export interface ZOptionalNumberOptions {
  min?: number
  integer?: boolean
}

/**
 * Número opcional desde un `<UiTextInput type="number">` (que entrega texto):
 * `''`/`null` → `null`; si no, se convierte y se valida (`min`, entero).
 */
export function zOptionalNumber(options: ZOptionalNumberOptions = {}) {
  let number = z.number({ invalid_type_error: 'Debe ser un número.' })
  if (options.integer) number = number.int('Debe ser un número entero.')
  if (options.min !== undefined) number = number.min(options.min, `Debe ser mayor o igual a ${options.min}.`)

  return z
    .union([z.string(), z.number(), z.null()])
    .optional()
    .transform((value, ctx) => {
      if (value === null || value === undefined) return null
      if (typeof value === 'string' && value.trim() === '') return null
      const parsed = Number(value)
      if (Number.isNaN(parsed)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: 'Debe ser un número.' })
        return z.NEVER
      }
      return parsed
    })
    .pipe(number.nullable())
}

/**
 * Valor obligatorio de una lista cerrada (enum del backend), típico de un
 * `<UiSelect>`. La entrada es `string` (el select arranca en `''`); la salida,
 * el tipo del enum.
 */
export function zRequiredEnum<const T extends readonly [string, ...string[]]>(values: T, requiredMessage: string) {
  return z
    .string({ required_error: requiredMessage, invalid_type_error: requiredMessage })
    .refine((value): value is T[number] => (values as readonly string[]).includes(value), requiredMessage)
}

/** Valor opcional de una lista cerrada: `''`/`null` → `null`; otro valor fuera de la lista es error. */
export function zOptionalEnum<const T extends readonly [string, ...string[]]>(
  values: T,
  invalidMessage = 'Selecciona una opción válida.'
) {
  return z
    .union([z.string(), z.null()])
    .optional()
    .refine(value => !value || (values as readonly string[]).includes(value), invalidMessage)
    .transform(value => (value ? (value as T[number]) : null))
}

/**
 * Id obligatorio elegido en un `<UiSelect>` de entidades (área, analito…),
 * que arranca en `''`. Para listas cerradas del backend usa `zRequiredEnum`.
 */
export function zRequiredId(requiredMessage: string) {
  return z
    .string({ required_error: requiredMessage, invalid_type_error: requiredMessage })
    .min(1, requiredMessage)
}

/** Id opcional de un `<UiSelect>` de entidades: `''`/`null` → `null`. */
export function zOptionalId() {
  return z
    .union([z.string(), z.null()])
    .optional()
    .transform(value => (value ? value : null))
}

/**
 * Número obligatorio desde un `<UiTextInput type="number">` (texto): vacío →
 * `requiredMessage`; si no, se convierte y se valida (`min`, entero).
 */
export function zRequiredNumber(requiredMessage: string, options: ZOptionalNumberOptions = {}) {
  return zOptionalNumber(options).refine((value): value is number => value !== null, requiredMessage)
}

/**
 * Objeto JSON escrito en un `<UiTextarea>` (p. ej. `placeholders`,
 * `report_settings`): vacío → `{}`; si no, debe ser JSON válido y un objeto
 * (no array ni primitivo). La salida ya es el objeto para el payload.
 */
export function zJsonObject(label = 'El valor') {
  return z
    .string()
    .optional()
    .transform((value, ctx) => {
      const text = value?.trim() ?? ''
      if (text === '') return {} as Record<string, unknown>
      let parsed: unknown
      try {
        parsed = JSON.parse(text)
      } catch {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: `${label} debe ser un JSON válido.` })
        return z.NEVER
      }
      if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: `${label} debe ser un objeto JSON ({ … }).` })
        return z.NEVER
      }
      return parsed as Record<string, unknown>
    })
}

/** Texto con formato legible de un objeto JSON, para precargar un campo `zJsonObject`. */
export function toJsonText(value: Record<string, unknown> | null | undefined) {
  return JSON.stringify(value ?? {}, null, 2)
}

/** Opciones de `<UiSelect>` a partir de un mapa valor → etiqueta. */
export function toSelectOptions<T extends string>(labels: Record<T, string>) {
  return (Object.entries(labels) as [T, string][]).map(([value, label]) => ({ value, label }))
}
