# ADR-landing-pocketbiz-rutas-esquema-rutas-montaje: Landing en "/" y aplicación bajo "/pocketbiz" dentro de una sola SPA

**Estado:** Propuesto
**Task relacionado:** TASK-landing-pocketbiz-rutas
**Fecha:** 2026-10-13

## Contexto
El usuario decidió que `/` cargue la landing y que el producto viva en `/pocketbiz/login`, `/pocketbiz/signup` y `/pocketbiz/**` (Q7). La investigación del task documenta el estado actual:

- Todo el producto cuelga de la raíz del router bajo `MainLayoutComponent` + `AuthGuard` (`app.routes.ts:8-13`), y las pantallas públicas bajo `authentication` (`app.routes.ts:131-136`, `auth.routes.ts:8-38`).
- `index.html:7` declara `<base href="/">`; `angular.json` no define `baseHref` ni `deployUrl`; no hay SSR (`angular.json`). El router usa `PathLocationStrategy` por defecto (`app.config.ts:20`, sin `withHashLocation`).
- Existen unas 140 navegaciones o enlaces absolutos (`routerLink="/…"`, `navigate(['/…'])`), 9 rutas absolutas en `assets/data/routes.json` y 19 specs con rutas literales.
- El backend solo expone `admin/` y `api/*` (`backend/config/urls.py:9-17`); no sirve el frontend. El repositorio no tiene configuración de despliegue (sin Docker, nginx ni CI).
- El DDR `DDR-landing-pocketbiz-rutas-landing-y-entradas` eligió construir la landing con componentes Angular de la plantilla (`ngbAccordion`, `NgbCollapse`, Bootstrap) dentro de `features/landing`.

## Decisión
**Una sola SPA con `<base href="/">` sin cambios**, y el prefijo `/pocketbiz` se introduce en el **router**, no en el build:

1. **Rutas de primer nivel** en `app.routes.ts`:
   - `''` → `LandingComponent` (carga diferida desde `features/landing`), **pública**, sin `AuthGuard` ni layout del panel.
   - `pocketbiz` → ruta padre con dos grupos de hijas:
     - **Públicas** (con `AuthLayoutComponent`): `login`, `signup`, `forgot`, `reset`, `page404`, `page500`. (`signin` pasa a llamarse `login` en la URL; el componente `SigninComponent` conserva su nombre.)
     - **Privadas** (`MainLayoutComponent` + `AuthGuard`, ruta `''`): todas las features actuales **con sus mismos paths relativos** (`dashboard`, `catalog/products`, `customers`, `sales/orders`, `expenses`, `reports`, y las demos de la plantilla).
   - `**` → `Page404Component` (se conserva).
2. **Prefijo único en código:** una constante `APP_BASE = '/pocketbiz'` y constantes de destino (`LOGIN`, `SIGNUP`, `DASHBOARD`) en un archivo de rutas del núcleo (`core/`), usada por guard, interceptor, header y componentes de auth. Los enlaces de plantillas HTML y `routes.json` se actualizan con el prefijo de forma **mecánica**; no se introduce una abstracción de rutas para ellos (evita sobreingeniería).
3. **`/pocketbiz` sin subruta:** la hija privada `''` redirige a `dashboard/main`; el `AuthGuard` envía a `/pocketbiz/login` si no hay sesión. Resultado: con sesión → dashboard; sin sesión → login (decisión de UX del DDR).
4. **Sin cambios en el backend ni en `proxy.conf.json`:** `/api` y `/admin/` no cambian. Si algún día un mismo host sirve SPA y Django, `/api/` y `/admin/` van a Django y `/` y `/pocketbiz/**` a la SPA; no hay colisión.
5. **Requisito de servidor** (fuera del repo): fallback de SPA estándar (cualquier ruta que no sea `/api` ni `/admin` devuelve `index.html`). No se requiere configurar una subruta de base.
6. **Orden de entrega recomendado:** (a) cambio mecánico de rutas con la app funcionando igual bajo `/pocketbiz`, en un commit propio; (b) la landing en otro commit. Así el cambio de rutas puede revertirse independientemente.
7. **Seguridad:** la landing es pública por diseño; `/pocketbiz/**` privado sigue protegido por `AuthGuard` en el cliente y, de forma efectiva, por el token y `CompanyAdminPermission` en el servidor (sin cambios). El guard no sustituye al backend.

## Alternativas consideradas
- **B. `ng build --base-href /pocketbiz/` + landing como artefacto aparte en `/`.** El `routerLink="/…"` absoluto se resolvería contra el base href, por lo que casi no cambiarían enlaces. Descartada: crea dos artefactos y exige configuración de servidor/proxy que el repo no tiene; la landing quedaría fuera de Angular (sin `ngbAccordion`, `NgbCollapse`, tokens SCSS compartidos), contradiciendo el DDR; el dev server necesitaría `--serve-path` y un segundo origen para `/`; y el CTA "Ir a mi panel" requeriría lógica duplicada de sesión.
- **C. `UrlSerializer`/`LocationStrategy` personalizado que anteponga `/pocketbiz` a toda URL generada.** Evita tocar los ~140 enlaces. Descartada: es un parche no estándar, frágil frente a actualizaciones de Angular y difícil de depurar; la deuda superaría al ahorro.
- **D. `withHashLocation()` (`/#/pocketbiz/login`).** No cumple la URL pedida y empeora SEO y enlaces compartibles.
- **E. Dos aplicaciones Angular (landing y panel) en el mismo workspace.** Aísla bundles pero duplica configuración, estilos y despliegue; innecesario para una página estática.

## Estrategia de rollback / mitigación
- **Cambio aditivo en datos:** no hay migraciones, API ni almacenamiento nuevos. El token de sesión en `localStorage` no depende de la ruta; no se invalidan sesiones.
- **Reversión:** revertir el/los commit(s) del PR restaura las rutas anteriores. Por eso se separan en commit mecánico de rutas y commit de landing (punto 6).
- **Mitigación de enlaces olvidados:** las redirecciones de compatibilidad (ver ADR `compatibilidad-urls-antiguas`) convierten cualquier ruta antigua a su equivalente bajo `/pocketbiz`, de modo que un enlace no actualizado no queda roto.
- **Verificación previa a fusionar:** `grep` de rutas literales antiguas sin resultados fuera de las redirecciones, `npm run build` y `npm run lint` en verde, y specs afectados actualizados.
- **Despliegue:** no cambia de topología; el único requisito nuevo es que el servidor haga fallback de SPA para `/pocketbiz/**` (suele estar ya para `/authentication/*`).

## Consecuencias
- **Más fácil:** una sola build, un solo despliegue y el dev server (`npm start`) sirven `/` y `/pocketbiz/**` sin configuración; la landing comparte componentes, tokens y estilos del panel; el cambio de rutas es mecánico y verificable con `grep` y los specs.
- **Más difícil:** hay que tocar ≈ 100 plantillas y 19 specs, y un enlace con prefijo olvidado solo se detecta por prueba o por la redirección; los tests que fijan rutas literales deben actualizarse en bloque.
- **Deuda aceptada:** los enlaces del panel quedan con el literal `/pocketbiz/…` repetido en plantillas (no hay helper para HTML); si el prefijo vuelve a cambiar, el costo es alto de nuevo. Se acepta porque no se prevé otro cambio.
- **Documentación:** actualizar `CLAUDE.md:15` y los documentos de diseño que citan `/authentication/*` y `/dashboard/*`.
