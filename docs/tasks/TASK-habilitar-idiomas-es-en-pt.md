# TASK-habilitar-idiomas-es-en-pt: Habilitar español, inglés y portugués en el sistema y la landing

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-habilitar-idiomas-es-en-pt
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/51

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-03 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-03 | INVESTIGATION → DESIGN | Diseño requerido: SI | delivery-start |
| 2026-11-03 | DESIGN → ARCHITECTURE | Veredicto NEEDS_ARCHITECTURE | delivery-start |
| 2026-11-03 | ARCHITECTURE → PLANNING | DDR y 2 ADR escritos | delivery-start |
| 2026-11-03 | PLANNING → ENGINEERING | Specification READY, PLAN v1 (COMPLETO) y PR abiertos | delivery-start |

## Investigación

### Requerimiento
Texto recibido (sin Trello):

> Habilitar 3 lenguajes: Spa = Spanish, En = English, Pr = Portugues. Al seleccionar uno se deben traducir todas las etiquetas o texto al lenguaje seleccionado; también aplica a la landing page. La URL debe reflejar el lenguaje seleccionado. La selección del usuario se guarda en el explorador; si no seleccionó un lenguaje, el por defecto es español. La selección se hace mediante un combobox en el menú superior a la derecha (hoy muestra una bandera del idioma); cambiar las banderas por Spa / En / Pr.

### Hechos encontrados
- `frontend/panel_admin/src/app/core/service/language.service.ts:5-26` — ya existe `LanguageService` con `ngx-translate`: idiomas `['en','es','de']`, por defecto `es` (no usa el idioma del navegador), guarda la elección con `LocalStorageService` bajo la clave `lang`.
- `frontend/panel_admin/src/app/core/service/storage.service.ts:19-27` — `LocalStorageService` **antepone `light_`/`dark_`** a toda clave según la variante de tema: la preferencia de idioma hoy cambia de «cajón» si cambia el tema.
- `frontend/panel_admin/src/app/app.config.ts:23-29` — `provideTranslateService({defaultLanguage:'es'})` + `provideTranslateHttpLoader` con `./assets/i18n/{lang}.json`. Sin `provideAppInitializer`: el idioma se carga de forma asíncrona tras el arranque.
- `frontend/panel_admin/src/assets/i18n/{es,en,de}.json` — 131-137 líneas cada uno; **solo contienen `MENUITEMS`** (etiquetas del menú lateral). `de.json` sobra.
- `frontend/panel_admin/src/app/layout/header/header.component.ts:56-58,125-130` y `header.component.html:18-36` — selector actual: `ngbDropdown` con imagen de bandera (`assets/images/flags/{us,spain,germany}.jpg`), opciones English/Spanish/German; `defaultFlag` = bandera de EE. UU. aunque el idioma por defecto es español.
- `frontend/panel_admin/src/app/layout/header/header.component.html:49` — «Logout» está hardcodeado en inglés.
- Solo **1 plantilla** usa el pipe `translate`: `layout/sidebar/sidebar.component.html:32-79`. Las otras ~150 plantillas HTML (7 700 líneas solo en `features/`, 72 plantillas) y ~75 archivos `.ts` con literales en español (`features/**`, etiquetas, mensajes de error, textos de toasts, constantes como `landing-content`) están **hardcodeados en español**.
- `frontend/panel_admin/src/app/features/landing/models/landing-content.ts` (importado en `landing.component.ts:7-24`) — todo el contenido de la landing vive como constantes TS en español; `landing.component.ts:62-67` tiene además textos del CTA («Ir a mi panel», «Empezar gratis»); `selectedPeriod = 'Este mes'` (`:44`).
- `frontend/panel_admin/src/app/core/routing/app-paths.ts:6-16` y `app.routes.ts:13-20,340-343` — rutas: `/` = landing, `/pocketbiz/**` = producto, `LEGACY_REDIRECTS` para URLs antiguas. **311 referencias a `pocketbiz` en 153 archivos no-spec** (routerLink/navigate con rutas absolutas), 27 usos de `APP_BASE`/`APP_PATHS`.
- Formatos de fecha: `date: 'dd/MM/yyyy'` / `'dd/MM/yyyy HH:mm'` en ~54 usos; no hay `LOCALE_ID`/`registerLocaleData` ni `currency` pipe (`grep` en `src/app`).
- `frontend/panel_admin/src/index.html:2` — `<html lang="en">` fijo; `app.component.ts:14` fija el título `PocketBiz`.
- `frontend/panel_admin/src/app/core/interceptor/error.interceptor.ts` y servicios `*-api.service.ts` / `models/api-error.ts` — los mensajes de error llegan del backend en texto (`detail`) y se muestran tal cual; `backend/config/settings/base.py:74-76` `LANGUAGE_CODE='es'`, `USE_I18N=True`, sin `LocaleMiddleware`; ~190 `ValidationError`/`detail` con mensajes en español en `backend/modules|accounts|shared`.
- `docs/adr/ADR-landing-pocketbiz-rutas-*` — URLs limpias (`PathLocationStrategy`), `<base href="/">`, y requisito de despliegue «el servidor devuelve `index.html` para toda ruta que no sea `/api/*`, `/admin/*` ni archivo estático».
- Tests: 1 227 casos `it()` en specs; 67 specs contienen aserciones sobre textos en español capitalizados.

### Hipótesis / supuestos no confirmados
- «Todas las etiquetas o texto» se interpreta como **todo el texto de interfaz del frontend** que alcanzan las pantallas del producto (menú, header, autenticación, features de negocio, configuración) y la landing. Se asume que **no** incluye: datos que escriben los usuarios (nombres de productos, clientes, notas), ni las páginas de demostración de la plantilla Oreva que no cuelgan del menú (`advance-table`, `apps`, `widget`, `ui`, `forms`, `charts`, `icons`, `maps`, `multilevel`, `tables`, `data-tables`, `email`, `calendar`, `extra-pages`).
- Los **mensajes de error que genera el backend** (`detail`, errores de validación) quedan en español en esta iteración; traducirlos exige un cambio de API (`Accept-Language` + `LocaleMiddleware` + catálogos `.po`) de otro orden de magnitud. Se registra como limitación conocida y seguimiento.
- «Pr = Portugues» se entiende como la **etiqueta visible** del selector. El código de URL será el estándar ISO 639-1 `pt` (`pr` no es un código de idioma); por eso las URLs serán `/es/…`, `/en/…`, `/pt/…`.
- Fechas, horas y montos conservan su formato actual (`dd/MM/yyyy`) en los tres idiomas; la localización de formatos de número/fecha queda fuera de alcance.
- La traducción al portugués y al inglés la redacta el agente y debería revisarla una persona nativa o de negocio.

### Módulos y dependencias relacionadas
Solo frontend (`frontend/panel_admin/src/app`): `core` (servicios, routing, interceptores), `layout` (header, sidebar, auth-layout), `authentication`, `features/*` (agenda, customers, dentistry, expenses, inventory, landing, personnel, products, purchases, reporting, sales, services, settings), `shared`. Sin cambios de backend, modelo de datos ni migraciones. Dependencias ya instaladas: `@ngx-translate/core` y `@ngx-translate/http-loader`.

### Implementaciones similares existentes
Menú lateral con claves `MENUITEMS.*` + pipe `translate` (`sidebar.component.html`). Rutas de compatibilidad con redirecciones y arranque que convierte `/#/…` (`core/routing/legacy-*`) — patrón de «normalizar la URL al arrancar».

### Comportamiento actual
El selector del header cambia el idioma del **menú lateral únicamente**; el resto de la aplicación y la landing siguen en español. La URL no refleja el idioma. La preferencia se guarda con prefijo de tema.

### Restricciones
`CLAUDE.md`: avisar antes de instalar dependencias (no se necesita ninguna); frontend con tipos explícitos, sin `any`, sin suscripciones colgadas; lenguaje visual en `docs/design/design-system.md`; servidor de despliegue debe devolver `index.html` para toda ruta que no sea `/api/*`, `/admin/*` ni estático (sigue cumpliéndose: los prefijos `/es|en|pt` no chocan con esas rutas).

### Riesgos identificados
1. **Volumen**: ~72 plantillas de features + ~75 archivos TS + landing + autenticación; riesgo de omisiones y de regresiones en 1 227 pruebas, muchas con textos en español.
2. **URLs**: 311 referencias absolutas `/pocketbiz/…`; reescribirlas es invasivo (ver ADR).
3. **Desfase de claves** entre idiomas (clave faltante visible en pantalla).
4. **Parpadeo / texto sin traducir** al arrancar si el JSON del idioma carga después del primer render.
5. Mensajes del backend seguirán en español (incoherencia visible al elegir en/pt).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — cambia el esquema de URLs de toda la aplicación, la estrategia de i18n de todo el frontend y afecta transversalmente a todos los módulos.

### Diseño requerido
**SI** — se modifica el selector de idioma del header, se añade a la landing y a las pantallas de autenticación, con estados y accesibilidad nuevos.

## Diseño
Ver [DDR-habilitar-idiomas-es-en-pt-selector-de-idioma](../design/DDR-habilitar-idiomas-es-en-pt-selector-de-idioma.md).

## Arquitectura
- [ADR-habilitar-idiomas-es-en-pt-url-con-idioma-y-preferencia](../adr/ADR-habilitar-idiomas-es-en-pt-url-con-idioma-y-preferencia.md)
- [ADR-habilitar-idiomas-es-en-pt-catalogos-de-traduccion](../adr/ADR-habilitar-idiomas-es-en-pt-catalogos-de-traduccion.md)

## Plan
[PLAN-2026-11-03-habilitar-idiomas-es-en-pt](../plans/PLAN-2026-11-03-habilitar-idiomas-es-en-pt.md) (v1, COMPLETO). Specification readiness: **READY**.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
