// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  // Sistema de diseño compartido (componentes Ui*, tokens, composables de formularios).
  extends: ['andromeda'],
  runtimeConfig: {
    // Base de la API solo para el servidor (SSR); si está vacía se usa la pública.
    // Se configura con NUXT_API_BASE_SERVER.
    apiBaseServer: '',
    public: {
      // Sin valor grabado: se llena desde NUXT_PUBLIC_API_BASE (frontend/.env).
      apiBase: ''
    }
  }
})
