/**
 * Clases compartidas por los controles de texto del núcleo (`UiTextInput`,
 * `UiTextarea`, `UiSelect`) para que las variantes de estilo HeroUI
 * (flat/bordered) y el estado inválido vivan en un solo lugar.
 */
export type UiFormControlVariant = 'flat' | 'bordered'

const base =
  'rounded-md border-2 px-3 text-sm text-text transition-colors duration-150 outline-none placeholder:text-default-500 disabled:cursor-not-allowed disabled:opacity-50'

const variants: Record<UiFormControlVariant, { normal: string, invalid: string }> = {
  flat: {
    normal:
      'border-transparent bg-default-100 hover:bg-default-200 focus:bg-default-100 focus:border-primary-500',
    invalid:
      'border-transparent bg-danger-50 text-danger-700 hover:bg-danger-100 focus:border-danger-500'
  },
  bordered: {
    normal:
      'border-default-200 bg-surface hover:border-default-400 focus:border-primary-500',
    invalid:
      'border-danger-500 bg-surface focus:border-danger-600'
  }
}

export function formControlClasses(variant: UiFormControlVariant, invalid: boolean): string {
  return `${base} ${invalid ? variants[variant].invalid : variants[variant].normal}`
}
