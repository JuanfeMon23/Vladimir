import { mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import ErrorPage from '#andromeda/error.vue'

enableAutoUnmount(afterEach)

// Vladimir no tiene `app/error.vue`: Nuxt usa el de la capa Andromeda.
async function show(statusCode: number) {
  return mountSuspended(ErrorPage, { props: { error: { statusCode, message: 'Traceback (crudo)', url: '/x', fatal: true } } })
}

describe('página de error de la capa (app/error.vue de Andromeda)', () => {
  it('404 muestra «No encontramos esta página»', async () => {
    const wrapper = await show(404)
    expect(wrapper.text()).toContain('No encontramos esta página')
    expect(wrapper.find('[role="status"]').exists()).toBe(true)
  })

  it('503 es una interrupción (alert) y no muestra el mensaje crudo', async () => {
    const wrapper = await show(503)
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('No encontramos esta página')
  })
})
