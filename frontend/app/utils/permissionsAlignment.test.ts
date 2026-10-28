import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import permissions from '../generated/permissions.json'

/**
 * Alineación backend ↔ frontend de los tags de acción. El contrato
 * `generated/permissions.json` lo genera el backend (`uv run python -m
 * app.core.permissions_export`); aquí se verifica que el código del frontend
 * coincide con él en ambos sentidos.
 */

const TAG = /vladimir\.[a-z0-9-]+\.[a-z0-9-]+/g

/** Literales con forma de tag que NO son permisos (claves de almacenamiento). */
const NOT_TAGS = new Set(['vladimir.sidebar.collapsed'])

/**
 * Tags asignables del backend que el frontend aún no usa en ninguna pantalla.
 * Cada entrada lleva su justificación; vacío = toda acción tiene pantalla.
 */
const TAGS_WITHOUT_SCREEN: Record<string, string> = {}

const root = process.cwd()

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) {
      return ['node_modules', '.nuxt', 'generated'].includes(entry.name) ? [] : sourceFiles(path)
    }
    return /\.(ts|vue)$/.test(entry.name) && !entry.name.endsWith('.test.ts') ? [path] : []
  })
}

function literalsInSource(): Map<string, string[]> {
  const found = new Map<string, string[]>()
  const files = [join(root, 'app'), ...readdirSync(join(root, 'layers')).map(layer => join(root, 'layers', layer))]
  for (const file of files.flatMap(sourceFiles)) {
    for (const tag of readFileSync(file, 'utf-8').match(TAG) ?? []) {
      if (!NOT_TAGS.has(tag)) found.set(tag, [...(found.get(tag) ?? []), file])
    }
  }
  return found
}

const contractTags = permissions.modules.flatMap(module => module.actions.map(action => action.tag))

describe('alineación de tags con el backend', () => {
  const used = literalsInSource()

  it('todo tag usado en el código del frontend existe en el contrato', () => {
    const unknown = [...used].filter(([tag]) => !contractTags.includes(tag)).map(([tag, files]) => `${tag} (${files[0]})`)
    expect(unknown, 'tags del frontend inexistentes en el backend').toEqual([])
  })

  it('todo tag asignable del contrato se usa en el frontend o está justificado', () => {
    const unused = permissions.modules
      .flatMap(module => module.actions)
      .filter(action => action.assignable && !used.has(action.tag) && !(action.tag in TAGS_WITHOUT_SCREEN))
      .map(action => action.tag)
    expect(unused, 'tags del backend sin uso en el frontend: úsalos o agrégalos a TAGS_WITHOUT_SCREEN').toEqual([])
  })

  it('TAGS_WITHOUT_SCREEN solo lista tags asignables que siguen sin uso', () => {
    for (const tag of Object.keys(TAGS_WITHOUT_SCREEN)) {
      expect(contractTags, tag).toContain(tag)
      expect(used.has(tag), `${tag} ya se usa: quítalo de TAGS_WITHOUT_SCREEN`).toBe(false)
    }
  })

  it('el contrato es de Vladimir y los eventos no son asignables', () => {
    expect(permissions.app).toBe('vladimir')
    const events = permissions.modules.flatMap(m => m.actions).filter(a => !a.assignable)
    expect(events.every(a => a.name.startsWith('Evento:'))).toBe(true)
  })
})
