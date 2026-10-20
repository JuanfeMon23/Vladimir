// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  // Sistema de diseño compartido (Andromeda) + sesión SSO y permisos del
  // ecosistema (leo-client). Andromeda va primero: los componentes de
  // leo-client usan sus Ui* y tokens.
  // PENDIENTE: leo-client se toma por ruta local al repo de Leo (hermano de
  // este proyecto); la forma de distribución final (dependencia git o paquete)
  // está por definir.
  extends: ['andromeda', '../../leo/client'],
  typescript: {
    // Las pruebas de leo-client (otro repo, otra versión de vue-router) no se chequean desde aquí.
    tsConfig: { exclude: ['../../../leo/client/**/*.test.ts'] }
  },
  runtimeConfig: {
    // Base de la API solo para el servidor (SSR); si está vacía se usa la pública.
    // Se configura con NUXT_API_BASE_SERVER. (Con leo-client la app es SPA: sin uso real.)
    apiBaseServer: '',
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
