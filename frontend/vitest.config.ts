import { defineVitestConfig } from '@nuxt/test-utils/config'

/**
 * Suite de pruebas del frontend (Vitest + @nuxt/test-utils).
 *
 * Todo corre en el entorno `nuxt` (happy-dom + auto-imports, alias `~` y
 * layers), para que utilidades, composables y componentes se prueben igual
 * que se usan en la app. Los tests viven junto al código que prueban
 * (`*.test.ts`, en el núcleo `app/` o en la layer dueña); Nuxt los ignora
 * para el auto-import y las rutas.
 */
export default defineVitestConfig({
  test: {
    // La caché de módulos en disco de Vitest 5 corrompe corridas repetidas con Nuxt.
    fsModuleCache: false,
    environment: 'nuxt',
    environmentOptions: {
      nuxt: {
        domEnvironment: 'happy-dom',
        // Valor falso propio de los tests: no dependen de `frontend/.env`.
        overrides: {
          runtimeConfig: {
            public: {
              apiBase: 'http://api.test/api/v1',
              // leo-client en `bff` contra una API falsa (apiBase cuelga de leo.apiBase).
              leo: { transport: 'bff', apiBase: 'http://api.test', publicUrl: 'http://api.test', appSlug: 'vladimir', appName: 'Vladimir' }
            }
          }
        }
      }
    },
    include: ['app/**/*.test.ts', 'layers/**/*.test.ts']
  }
})
