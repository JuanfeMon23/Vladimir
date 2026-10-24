import { mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { signInWith } from '#leo-client/testing/session'
import App from './app.vue'

enableAutoUnmount(afterEach)

describe('app.vue', () => {
  it('monta UiToaster para que los toasts sean visibles', async () => {
    signInWith([])
    const wrapper = await mountSuspended(App)
    expect(wrapper.findComponent({ name: 'UiToaster' }).exists()).toBe(true)
  })
})
