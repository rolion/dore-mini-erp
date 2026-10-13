# ADR-landing-pocketbiz-rutas-url-sin-hash: URLs limpias (`/pocketbiz/login`) en lugar de `/#/…`

**Estado:** Propuesto
**Task relacionado:** TASK-landing-pocketbiz-rutas
**Fecha:** 2026-10-13

## Contexto
`delivery-engineer` reportó `ARCHITECTURE_REVIEW_REQUIRED` al implementar `PLAN-2026-10-13-landing-pocketbiz-rutas` (v1): la aplicación usa `HashLocationStrategy` (`frontend/panel_admin/src/app/app.config.ts:6,23`). Las URLs reales son `http://host/#/pocketbiz/login`, y una URL `/pocketbiz/login` sin hash carga la landing. La investigación y el ADR [esquema-rutas-montaje](ADR-landing-pocketbiz-rutas-esquema-rutas-montaje.md) dieron por hecho `PathLocationStrategy` porque un `grep` no buscó `HashLocationStrategy`; esa premisa era errónea. El resto de aquel ADR (una SPA, prefijo en el router, `<base href="/">` sin cambios) sigue vigente y es independiente de la estrategia.

Hechos verificados para esta decisión:
- El requisito del usuario (Q7) es explícito: `/` = landing y `/pocketbiz/login`, `/pocketbiz/signup`, `/pocketbiz/**`.
- Ningún código depende del hash: `grep` de `location.hash`, `window.location`, `href="#/` y de `Hash` en `src/app` solo encuentra el provider (`app.config.ts:6,23`).
- `<base href="/">` ya es absoluto (`index.html:7`), y los recursos relativos (`./assets/i18n/` del loader de traducciones, `app.config.ts:29`) se resuelven contra él: no cambian bajo rutas profundas.
- El backend solo expone `admin/` y `api/*` (`backend/config/urls.py:9-17`); el repositorio no tiene configuración de despliegue.
- Con la estrategia de hash el servidor solo ve `/`, por eso hoy no necesita fallback de SPA; con URLs limpias lo necesita para `/pocketbiz/**` y para recargas profundas.
- El producto está "en construcción" (`CLAUDE.md`): no hay un despliegue de producción documentado y el entorno de desarrollo (`ng serve`) ya sirve `index.html` como fallback para cualquier ruta.

## Decisión
1. **Pasar a `PathLocationStrategy`** (la predeterminada): eliminar el provider `{ provide: LocationStrategy, useClass: HashLocationStrategy }` y su import de `app.config.ts`. `<base href="/">` no cambia.
2. **Compatibilidad con URLs con hash ya compartidas.** Un arranque único, en la propia aplicación, que si la URL llega como `/#/<ruta>` navegue a `<ruta>` reemplazando la entrada del historial (`replaceUrl`). Las redirecciones del ADR [compatibilidad-urls-antiguas](ADR-landing-pocketbiz-rutas-compatibilidad-urls-antiguas.md) resuelven después las rutas antiguas (`/#/authentication/signin` → `/pocketbiz/login`). Se retira junto con esas redirecciones.
3. **Requisito de despliegue explícito:** el servidor que sirva la SPA debe devolver `index.html` para cualquier ruta que no sea `/api/*`, `/admin/*` ni un archivo estático. Se documenta en `CLAUDE.md` (sección Comandos/Reglas de frontend). Es un requisito previo al primer despliegue con URLs limpias; no se configura infraestructura en este task porque no existe en el repo.
4. **Sin interruptor de configuración.** No se añade un flag `useHash` por entorno (sobreingeniería: duplicaría pruebas y rutas de código).

## Alternativas consideradas
- **Mantener `HashLocationStrategy`** (`/#/pocketbiz/login`). Cero cambios de infraestructura, pero incumple el requisito explícito de Q7, las URLs compartidas conservarían el `#`, y la landing en `/` convive con un producto en `/#/pocketbiz/*`. Descartada por incumplir el requisito; queda como respaldo de una línea si no se puede configurar el fallback.
- **Hash + reescritura en servidor** (servir `/pocketbiz/*` y redirigir a `/#/pocketbiz/*`). Da URLs "limpias" de entrada pero la barra termina con `#`; exige la misma configuración de servidor y añade un redireccionamiento frágil. Descartada.
- **`PathLocationStrategy` con flag por entorno** (`environment.useHash`). Permite revertir sin recompilar, pero mantiene dos modos probables y una configuración extra que nadie usará. Descartada (YAGNI).
- **Prerender/SSR de la landing.** Mejoraría el SEO, pero no es necesario para la URL y excede el alcance (fuera de alcance en el plan).

## Estrategia de rollback / mitigación
- **Cambio acotado y reversible:** es la eliminación de un provider y el arranque de compatibilidad. Revertir el commit o volver a agregar la línea del provider restaura la estrategia anterior; el arranque de compatibilidad es inofensivo en modo hash (no actúa si la URL ya es `/#/…` interna del router).
- **Orden de despliegue:** primero configurar el fallback del servidor, después publicar el frontend. Si el fallback no estuviera disponible, mantener el provider de hash (rollback) hasta tenerlo; en ese caso Q7 queda parcialmente cumplido (URLs con `#`) y debe informarse al usuario.
- **Verificación previa:** carga directa de `/pocketbiz/login`, `/pocketbiz/sales/orders/<id>` y recarga profunda en `ng serve`; `/#/authentication/signin` redirige a `/pocketbiz/login`; `/api/*` y `/admin/` no se interceptan.
- **Datos y sesión:** el token sigue en `localStorage` del mismo origen; no se invalida ninguna sesión.

## Consecuencias
- **Más fácil:** URLs reales `/` y `/pocketbiz/login` tal como pidió el usuario; enlaces compartibles limpios; la landing en `/` queda desacoplada del producto en la barra de direcciones.
- **Más difícil:** el servidor debe tener fallback de SPA (hoy no hace falta); un 404 de servidor aparecería en recargas profundas si falta; hay que mantener el arranque de compatibilidad hasta retirar las redirecciones.
- **Deuda aceptada:** requisito de despliegue sin infraestructura versionada en el repo; si el repo adopta nginx/Docker más adelante, el fallback debe pasar a esa configuración.
- **Cambios derivados en el plan:** modificar `app.config.ts` y el arranque de compatibilidad, pruebas de ese arranque, nota en `CLAUDE.md`, y verificar en el navegador con URLs limpias (no hash). Los criterios de aceptación AC-03/AC-05/AC-08 se vuelven verificables sobre la URL real.
