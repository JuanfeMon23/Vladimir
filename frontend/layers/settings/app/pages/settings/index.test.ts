import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { signInWith } from '#leo-client/testing/session'
import { flushAll } from '#andromeda/testing/dom'
import { apiError } from '~/testing/apiError'
import { ALL_SETTINGS_TAGS } from '~/testing/session'
import SettingsPage from './index.vue'
import { useSettingsScreen } from '../../composables/useSettingsScreen'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

function setting(over: Record<string, unknown> = {}) {
  return {
    key: 'pagination.max_page_size', type: 'int', value: 200, default: 200, min: 10, max: 500, unit: null,
    description: 'Tamaño máximo de página', version: 3, requires_security_permission: false,
    updated_at: null, updated_by: null, updated_by_username: null, ...over
  }
}
const LIST = { groups: [{ group: 'Paginación', settings: [setting()] }] }
const VIEW = 'vladimir.settings.view'
const KEY_PATH = '/settings/pagination.max_page_size'

beforeEach(() => {
  fake.reset()
  document.body.innerHTML = ''
  fake.routes['GET /settings'] = LIST
})

describe('ruta y nombres de permisos de ajustes', () => {
  it('/settings exige vladimir.settings.view', () => {
    expect((useRouter().resolve('/settings').meta as { leo?: { tag?: string } }).leo?.tag).toBe(VIEW)
  })

  it('registra nombres legibles de los 3 permisos', () => {
    for (const tag of ALL_SETTINGS_TAGS) expect(permissionName(tag), tag).toMatch(/ajustes/i)
  })
})

describe('página de ajustes', () => {
  it('carga con GET /settings y lista los ajustes por grupo', async () => {
    signInWith([VIEW])
    const wrapper = await mountSuspended(SettingsPage)
    await flushAll()
    expect(fake.requests).toHaveBeenCalledWith('GET', '/settings', undefined)
    expect(wrapper.text()).toContain('Ajustes del sistema')
    expect(wrapper.text()).toContain('Tamaño máximo de página')
  })

  it('sin vladimir.settings.edit no hay controles de edición y el valor sale como texto; con él sí', async () => {
    signInWith([VIEW])
    const readOnly = await mountSuspended(SettingsPage)
    await flushAll()
    expect(readOnly.find('input').exists()).toBe(false)
    expect(readOnly.find('[role="switch"]').exists()).toBe(false)
    expect(readOnly.findAll('button').map(b => b.text())).not.toContain('Guardar')
    expect(readOnly.findAll('button').map(b => b.text())).not.toContain('Restablecer')
    expect(readOnly.find('[data-testid="setting-readonly"]').text()).toContain('200')

    signInWith([VIEW, 'vladimir.settings.edit'])
    const editable = await mountSuspended(SettingsPage)
    await flushAll()
    expect(editable.find('input').attributes('disabled')).toBeUndefined()
    expect(editable.findAll('button').map(b => b.text())).toEqual(expect.arrayContaining(['Guardar', 'Restablecer']))
  })

  it('sin vladimir.settings.edit-security un ajuste de seguridad es solo texto, con su motivo; con él se edita', async () => {
    fake.routes['GET /settings'] = {
      groups: [{ group: 'Seguridad', settings: [setting({ key: 'login.lockout', value: 5, default: 5, requires_security_permission: true })] }]
    }
    signInWith([VIEW, 'vladimir.settings.edit'])
    const locked = await mountSuspended(SettingsPage)
    await flushAll()
    expect(locked.find('input').exists()).toBe(false)
    expect(locked.findAll('button').map(b => b.text())).not.toContain('Guardar')
    expect(locked.find('[data-testid="setting-readonly"]').text()).toContain('5')
    expect(locked.find('[data-testid="setting-locked"]').exists()).toBe(true)

    signInWith(ALL_SETTINGS_TAGS)
    const editable = await mountSuspended(SettingsPage)
    await flushAll()
    expect(editable.find('input').exists()).toBe(true)
    expect(editable.find('[data-testid="setting-readonly"]').exists()).toBe(false)
  })
})

describe('useSettingsScreen (permisos y fetchers)', () => {
  async function screen(tags: string[]) {
    signInWith(tags)
    let admin!: ReturnType<typeof useSettingsScreen>
    await mountSuspended({ setup() { admin = useSettingsScreen(); return () => null } })
    return admin
  }
  const secure = setting({ key: 'login.lockout', requires_security_permission: true })

  it('view: nada es editable; edit: lo común; edit-security: también lo de seguridad', async () => {
    expect((await screen([VIEW])).canEditSetting(setting() as never)).toBe(false)
    const edit = await screen([VIEW, 'vladimir.settings.edit'])
    expect(edit.canEditSetting(setting() as never)).toBe(true)
    expect(edit.canEditSetting(secure as never)).toBe(false)
    expect((await screen(ALL_SETTINGS_TAGS)).canEditSetting(secure as never)).toBe(true)
  })

  it('guardar hace PUT /settings/{key} con valor, motivo y versión esperada', async () => {
    const admin = await screen(ALL_SETTINGS_TAGS)
    await admin.load()
    const item = admin.groups[0]!.settings[0]!
    admin.setDraft(item, '100')
    expect(admin.askSave(item)).toBe(true)
    admin.reason = 'Reducir la carga'
    fake.routes[`PUT ${KEY_PATH}`] = { ...item, value: 100, version: 4 }
    await admin.confirmSave()
    expect(fake.bodies('PUT', KEY_PATH)).toEqual([
      { value: 100, reason: 'Reducir la carga', expected_version: 3 }
    ])
    expect(admin.groups[0]!.settings[0]!.value).toBe(100)
  })

  it('el historial pide GET /settings/{key}/history con page', async () => {
    const admin = await screen(ALL_SETTINGS_TAGS)
    await admin.load()
    fake.routes[`GET ${KEY_PATH}/history`] = { items: [], page: 2, page_size: 20, total: 0 }
    await admin.openHistory(admin.groups[0]!.settings[0]!)
    await admin.setHistoryPage(2)
    expect(fake.requests).toHaveBeenLastCalledWith('GET', `${KEY_PATH}/history`, { params: { page: 2 } })
  })

  it('un error de rango sale en español y un error de carga no muestra el texto crudo', async () => {
    const admin = await screen(ALL_SETTINGS_TAGS)
    await admin.load()
    const item = admin.groups[0]!.settings[0]!
    admin.setDraft(item, '20')
    admin.askSave(item)
    admin.reason = 'Prueba de rango'
    fake.failures[`PUT ${KEY_PATH}`] = apiError({ code: 'setting_out_of_range', message: 'raw', details: { min: 10, max: 500 } }, 422)
    await admin.confirmSave()
    expect(admin.saveError).toMatch(/fuera del rango/)

    fake.failures['GET /settings'] = apiError({ code: 'internal_error', message: 'Traceback (most recent call last)' }, 500)
    await admin.load()
    expect(admin.loadError).toBeTruthy()
    expect(admin.loadError).not.toContain('Traceback')
  })
})
