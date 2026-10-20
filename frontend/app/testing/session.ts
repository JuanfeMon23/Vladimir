import { useState } from '#imports'

/**
 * Deja una sesión de Leo autenticada con los tags dados (solo tests de
 * componentes/páginas con `LeoCan`/`useCan`/middleware). Nuxt no auto-importa `app/testing/`.
 */
export function signInWith(permissions: string[]) {
  useState('leo-session').value = {
    status: 'authenticated',
    me: {
      user: { id: 'u1', username: 'ana', email: 'a@x.co', first_name: 'Ana', last_name: 'Pérez' },
      session: { id: 's', expires_at: '', last_activity_at: '', idle_timeout_seconds: 0 },
      permissions,
      applications: []
    }
  }
}

export const ALL_LAB_AREAS_TAGS = [
  'vladimir.lab-areas.view',
  'vladimir.lab-areas.create',
  'vladimir.lab-areas.edit',
  'vladimir.lab-areas.change-status',
  'vladimir.lab-areas.assign-manager'
]
