# Vladimir — frontend

Aplicación Nuxt 4 (Vue 3, TypeScript, Tailwind CSS v4). La puesta en marcha, las variables de entorno, las pruebas y la arquitectura están en el [README de la raíz](../README.md).

Referencia rápida (con `pnpm`; no uses `npm` ni `yarn`):

```bash
cp .env.example .env     # completa NUXT_PUBLIC_API_BASE
pnpm install
pnpm run dev             # http://localhost:3000
pnpm exec vitest run     # pruebas
pnpm exec nuxi typecheck # tipos
```

El catálogo de componentes reutilizables está en `app/components/ui/CATALOG.md`.
