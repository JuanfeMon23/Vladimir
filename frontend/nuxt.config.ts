// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  // Sistema de diseño compartido (Andromeda) + sesión SSO y permisos del
  // ecosistema (leo-client, dependencia git fijada a una etiqueta del repo de
  // Leo). Andromeda va primero: los componentes de leo-client usan sus Ui* y tokens.
  extends: ['andromeda', 'leo-client'],
  typescript: {
    // La config de la capa leo-client (dependencia) no se chequea desde aquí.
    tsConfig: { exclude: ['../node_modules/leo-client/**', '../node_modules/.pnpm/leo-client*/**'] }
  },
  runtimeConfig: {
    public: {
      // Sin valor grabado: se llena desde NUXT_PUBLIC_API_BASE (frontend/.env).
      apiBase: '',
      // Claves definidas por leo-client; aquí los valores fijos de Vladimir (transporte `bff`).
      // `apiBase` y `publicUrl` vienen del .env (NUXT_PUBLIC_LEO_API_BASE / _PUBLIC_URL).
      leo: {
        transport: 'bff',
        authPath: '/auth',
        // Debe coincidir con la redirect_uri registrada en Leo: http://localhost:3000/leo/callback
        callbackPath: '/leo/callback',
        appSlug: 'vladimir',
        appName: 'Vladimir'
      }
    }
  }
})
