import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h } from 'vue'
import { describe, expect, it } from 'vitest'
import { signInWith } from '#leo-client/testing/session'

const TAGS = { create: 'a.create', edit: 'a.edit', publish: 'a.publish', retire: 'a.retire' }

async function resolve(permissions: string[], tags: typeof TAGS | undefined) {
  signInWith(permissions)
  let result!: ReturnType<typeof useVersionPermissions>
  await mountSuspended(defineComponent({
    setup() {
      result = useVersionPermissions(() => tags)
      return () => h('div')
    }
  }))
  return { ...result }
}

describe('useVersionPermissions', () => {
  it('cada acción exige su propio tag', async () => {
    expect(await resolve(['a.edit', 'a.retire'], TAGS)).toEqual({ create: false, edit: true, publish: false, retire: true })
  })

  it('sin tag la acción no se permite (fail-closed)', async () => {
    expect(await resolve([], undefined)).toEqual({ create: false, edit: false, publish: false, retire: false })
  })
})
