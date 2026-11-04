# PLAN-2026-11-03-habilitar-idiomas-es-en-pt (v1)

**Task:** TASK-habilitar-idiomas-es-en-pt · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** [DDR selector de idioma](../design/DDR-habilitar-idiomas-es-en-pt-selector-de-idioma.md) · [ADR URL con idioma y preferencia](../adr/ADR-habilitar-idiomas-es-en-pt-url-con-idioma-y-preferencia.md) · [ADR catálogos de traducción](../adr/ADR-habilitar-idiomas-es-en-pt-catalogos-de-traduccion.md)

## Objective
Que el frontend (panel, autenticación y landing) pueda usarse en español, inglés y portugués: selector `Spa / En / Pr` en la parte superior derecha, todo el texto de interfaz traducido, la URL con prefijo de idioma (`/es|en|pt/…`) y la elección guardada en el navegador (español por defecto).

## Context
Resumen en `docs/tasks/TASK-habilitar-idiomas-es-en-pt.md`. Hoy solo el menú lateral está traducido; el resto del texto es español hardcodeado.

# Specification

## Domain context
Solo presentación (frontend). Sin Bounded Context de negocio afectado; sin backend, modelo de datos ni migraciones.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Idioma activo | Idioma con que se muestra la interfaz (`es`, `en`, `pt`) | este plan |
| Preferencia | Idioma elegido por la persona y guardado en el navegador | requerimiento |
| Prefijo de idioma | Primer segmento de la URL: `es`, `en` o `pt` | ADR URL |
| Etiqueta del selector | `Spa`, `En`, `Pr` (texto visible); distinta del código de URL (`es`, `en`, `pt`) | requerimiento / DDR |

## Current behavior
- Selector con banderas en `header.component.html:18-36` (en/es/de); traduce solo `MENUITEMS` (`sidebar.component.html`).
- Preferencia en `LocalStorageService` clave `lang` con prefijo de tema (`storage.service.ts:19-27`).
- URL sin idioma: `/` landing, `/pocketbiz/**` producto (`app.routes.ts`, `app-paths.ts`).
- Landing, autenticación y features en español hardcodeado.

## Expected behavior
1. Idiomas soportados: Español (`es`), Inglés (`en`), Portugués (`pt`). Se elimina alemán.
2. El selector del header (derecha) muestra `Spa`, `En` o `Pr` según el idioma activo y lista las tres opciones; no hay banderas.
3. Al elegir un idioma, toda la interfaz visible pasa a ese idioma sin recargar la página, la URL cambia de prefijo conservando ruta, query y fragmento, y la elección se guarda.
4. Al abrir cualquier URL: si trae prefijo, se usa ese idioma; si no, el idioma guardado; si no hay, español. Una URL sin prefijo se reemplaza por la versión con prefijo.
5. La landing y las pantallas de autenticación incluyen el selector y se traducen igual.

## Domain rules / invariants
- **INV-01** (nueva): el idioma activo siempre es uno de `es|en|pt`.
- **INV-02** (nueva): el prefijo de la URL siempre coincide con el idioma activo en pantallas del router.
- **INV-03** (nueva): `es.json`, `en.json` y `pt.json` tienen exactamente las mismas claves, ningún valor vacío y las mismas interpolaciones.
- **INV-04** (nueva): `/api/*` y `/admin/*` nunca llevan prefijo.
- **INV-05** (nueva): la preferencia solo se escribe cuando la persona elige en el selector.

## Acceptance criteria
- **AC-01** El header muestra un selector a la derecha con la etiqueta `Spa`/`En`/`Pr` del idioma activo (sin imágenes de bandera) y una lista con `Spa · Español`, `En · English`, `Pr · Português`.
- **AC-02** Sin preferencia ni prefijo, abrir `/` o `/pocketbiz/login` redirige (reemplazando el historial) a `/es` y `/es/pocketbiz/login` y muestra español.
- **AC-03** Elegir `En` en cualquier pantalla del producto traduce el texto de esa pantalla, el menú, el header y los diálogos/toasts del frontend al inglés, y la URL pasa a `/en/<misma ruta>` con query y fragmento intactos; igual para `Pr` → `/pt/…`.
- **AC-04** Tras elegir un idioma y recargar, o abrir una URL sin prefijo en una pestaña nueva, se usa el idioma guardado y la URL lo refleja.
- **AC-05** Abrir un enlace con prefijo (`/pt/pocketbiz/login`) muestra portugués aunque la preferencia guardada sea otra y **no** modifica la preferencia guardada.
- **AC-06** La landing en `/es`, `/en` y `/pt` muestra todo su contenido (navegación, secciones, planes, FAQ, CTA, pie) en el idioma correspondiente, con el selector en la barra superior derecha; los CTA llevan a `/<lang>/pocketbiz/signup|dashboard`.
- **AC-07** Login, registro, olvido y restablecer contraseña se traducen y muestran el selector.
- **AC-08** Todas las pantallas del producto alcanzables desde el menú (agenda, odontología, personal, catálogo, clientes, ventas, gastos, reportes, inventario, compras, configuración, módulos) no contienen texto visible hardcodeado en español: sin claves visibles y sin texto mezclado en los tres idiomas.
- **AC-09** Los catálogos `es/en/pt` tienen las mismas claves (INV-03) verificado por prueba automatizada.
- **AC-10** Cambiar de idioma no pierde lo escrito en un formulario ni dispara el aviso de cambios sin guardar; no recarga la ruta.
- **AC-11** El atrás/adelante del navegador y la recarga profunda (`/en/pocketbiz/sales/orders/12`) funcionan; las URLs antiguas (`/#/…`, `/authentication/signin`, `/dashboard/main`, sin prefijo) siguen resolviendo y terminan con prefijo.
- **AC-12** `<html lang>` refleja el idioma activo.
- **AC-13** Con el almacenamiento del navegador bloqueado el sistema funciona (español o idioma de la URL) sin errores.

## Edge cases / Error cases
- **EDGE-01** Prefijo no soportado (`/fr/pocketbiz/login`): se trata como ruta sin prefijo → 404 traducida en el idioma activo.
- **EDGE-02** Valor guardado inválido o antiguo (`de`, `light_lang`): se ignora y se usa español.
- **EDGE-03** Falla la carga de un catálogo: se mantiene el idioma anterior, aviso breve, selector operativo; si el fallo es el del idioma inicial, se usa español.
- **EDGE-04** Clave faltante en runtime (no debería ocurrir por INV-03): se muestra el español, nunca la clave.
- **EDGE-05** Redirecciones por 401 / módulo deshabilitado / guards conservan el idioma activo.
- **EDGE-06** Rutas con parámetros, query y fragmento (`/pt/pocketbiz/inventory/stock/3/4?x=1#a`) conservan todo al cambiar de idioma.
- **EDGE-07** Mensajes de error devueltos por el backend se muestran tal como llegan (español) — limitación declarada.
- **EDGE-08** Nombres de módulos/estados que llegan del backend como texto: el frontend los mapea por código a claves; si no hay clave, se muestra el texto recibido.

## Authorization / permissions
Sin cambios. El idioma no afecta permisos ni datos; el backend sigue aplicando `company_id` y permisos.

## API contract
Sin cambios. (`/api/*` sin prefijo, INV-04.) El backend no recibe ni devuelve idioma en esta iteración.

## UI behavior
- **UI-01** Selector del header: `app-language-selector` (DDR; patrón `ngbDropdown` del header), etiqueta `Spa|En|Pr`, icono `globe`, `aria-label` traducido, opción activa con `aria-current`.
- **UI-02** Selector en la landing: mismo componente en la barra superior derecha, estilo de enlaces de la barra (`landing-header.scss`); también dentro del menú colapsado móvil.
- **UI-03** Selector en `auth-layout`: arriba a la derecha, compacto, sobre las pantallas de autenticación (plantilla «Autenticación», `design-system.md` §5).
- **UI-04** Estados: cargando catálogo (mantiene idioma anterior), error de carga (aviso breve), éxito (cambio inmediato).
- **UI-05** Accesibilidad: foco por teclado, contraste en tema claro y oscuro (`design-system.md` §7), nombres de opciones en su propio idioma.
- **UI-06** Se eliminan las banderas (`assets/images/flags/*`) y la opción alemana.

## Non-functional requirements
- Sin dependencias nuevas.
- El cambio de idioma se percibe inmediato (catálogo pequeño en una sola petición; cacheable).
- Sin suscripciones colgadas ni `any` (`CLAUDE.md`).
- Sin texto visible hardcodeado nuevo (regla añadida a `design-system.md`).

## Out of scope
- Mensajes de error/validación generados por el backend y cualquier cambio de API, `Accept-Language`, `.po`.
- Localización de formato de fechas, horas, números y moneda (siguen `dd/MM/yyyy` y «Bs»).
- Datos escritos por los usuarios y datos semilla del backend.
- Páginas de demostración de la plantilla Oreva no enlazadas desde el menú.
- Emails, PDFs u otros artefactos fuera del frontend. SEO (`hreflang`, SSR/prerender).
- Revisión profesional de traducciones.

## Open questions (no bloquean)
- **OQ-01** ¿Se desea un seguimiento para traducir los mensajes del backend? (se propone como task aparte).
- **OQ-02** ¿El código de URL `pt` es aceptable para la etiqueta «Pr»? (se asume sí; cambiarlo es una constante).
- **OQ-03** ¿Fechas y moneda deben adaptarse por idioma (p. ej. `MM/dd/yyyy` en inglés)? (se asume no).

# Test Specification

## Unit tests
- `LanguageService`: resolución (prefijo > preferencia > `es`), idioma inválido, persistencia solo al elegir, almacenamiento bloqueado, `html lang`. (AC-02, AC-04, AC-05, AC-12, AC-13, INV-01, INV-05, EDGE-02)
- `LanguageUrlSerializer`: parse quita el prefijo y fija el idioma; serialize lo antepone; query/fragmento/parámetros intactos; `/api`, `/admin` sin prefijo; prefijo inválido. (AC-03, AC-11, INV-02, INV-04, EDGE-01, EDGE-06)
- Paridad de catálogos `es/en/pt`: claves, vacíos, interpolaciones. (AC-09, INV-03)
- Clave faltante → respaldo español. (EDGE-04)

## Integration tests
- `LanguageSelectorComponent` (render, selección, `aria-current`, etiqueta `Spa|En|Pr`, sin `<img>`). (AC-01, UI-01, UI-05)
- Router real con `RouterTestingHarness`: `/`, `/pocketbiz/login`, URL profunda con query/fragmento, legacy `/#/…` y `/authentication/signin`, cambio de idioma sin navegación ni `unsavedChangesGuard`, redirect de 401 conserva prefijo. (AC-02, AC-10, AC-11, EDGE-05)
- Componentes por feature: cada spec existente pasa con `provideTestTranslations()` (afirmaciones en español); una prueba por feature en `en` y `pt` que verifica un par de textos clave. (AC-03, AC-08)
- Landing: contenido en los 3 idiomas, CTA con prefijo. (AC-06)
- Autenticación: textos y selector. (AC-07)

## E2E
**NO** automatizado (no hay Playwright instalado y requeriría dependencia). La verificación de extremo a extremo (cambiar idioma en landing, login y 3-4 pantallas; recarga; atrás/adelante; tema oscuro) la hace `delivery-publish` manualmente con el navegador integrado y queda registrada en el PR.

## Regression tests
Las 1 227 pruebas existentes deben seguir verdes (`npm test`), `npm run lint` y `npm run build` sin errores. Se ajustan solo las que comparan `router.url`/`Location.path()` (ahora con prefijo) o dependen del selector antiguo.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | spec `LanguageSelectorComponent` + revisión visual |
| AC-02 | spec `LanguageService`/router harness (`/` y `/pocketbiz/login`) |
| AC-03 | specs de serializer, selector y de features en `en`/`pt` + revisión manual |
| AC-04 | spec `LanguageService` (preferencia) + manual con recarga |
| AC-05 | spec `LanguageService` (prefijo gana, no escribe preferencia) |
| AC-06 | spec landing × 3 idiomas + manual |
| AC-07 | specs de signin/signup/forgot/reset |
| AC-08 | specs por feature + paridad de catálogos + búsqueda de literales (`grep`) documentada en publish + revisión manual por pantalla |
| AC-09 | spec de paridad de catálogos |
| AC-10 | router harness con `unsavedChangesGuard` + spec de formulario |
| AC-11 | router harness (recarga profunda, legacy) + manual atrás/adelante |
| AC-12 | spec `LanguageService` |
| AC-13 | spec `LanguageService` con `localStorage` que lanza |

# Implementation Plan

## Architecture considerations
Ver los dos ADR. Puntos clave: `UrlSerializer` propio para no tocar las 311 referencias a `/pocketbiz`; catálogos JSON por idioma con claves anidadas por área; carga previa al render con `provideAppInitializer`.

## Proposed solution
1. Infraestructura (`core/i18n/`): `SUPPORTED_LANGUAGES`, `LanguageService` reescrito, `LanguageUrlSerializer`, normalización inicial, helper de pruebas.
2. Componente compartido `app-language-selector` usado en header, landing y auth-layout.
3. Migración de texto a claves en 4 olas: (a) layout/header/sidebar/auth/shared/core, (b) landing, (c) features pequeñas, (d) features grandes.

## Files/components affected
- **Frontend core:** `core/service/language.service.ts` (+spec), nuevo `core/i18n/language-url.serializer.ts`, `core/i18n/language.config.ts`, `core/i18n/testing.ts`; `app.config.ts` (serializer, initializer, `defaultLanguage`), `core/service/storage.service.ts` (sin cambio; la clave nueva usa `localStorage` directo), `index.html` (`lang`).
- **Layout/shared:** `layout/header/*`, `layout/app-layout/auth-layout/*`, nuevo `shared/components/language-selector/*`, `layout/sidebar/*` (claves).
- **Assets:** `assets/i18n/{es,en,pt}.json` (crecen), borrar `de.json` y `assets/images/flags/*`.
- **Autenticación y landing:** `authentication/*`, `features/landing/**` (`landing-content.ts` → claves).
- **Features:** `features/{agenda,customers,dentistry,expenses,inventory,personnel,products,purchases,reporting,sales,services,settings}/**` (≈72 plantillas, ≈75 archivos TS).
- **Tests:** specs afectadas (67 con textos) y nuevas de paridad/serializer/selector.
- **Docs:** `docs/design/design-system.md` (ya actualizado en este PR), `CLAUDE.md` (nota de URLs con prefijo de idioma y clave de preferencia).
- **Backend / migraciones:** ninguno.

## Implementation steps
1. **PoC del serializer** (INV-02, INV-04, AC-11): `LanguageUrlSerializer` + pruebas con las rutas reales; verificar en `npm start` carga directa, recarga profunda, atrás/adelante, `/#/…`, redirects legacy. Si falla → `ARCHITECTURE_REVIEW_REQUIRED` (alternativa: ruta `:lang`).
2. **`LanguageService`** (INV-01, INV-05, AC-02, AC-04, AC-05, AC-12, AC-13, EDGE-02/03): idiomas `es|en|pt`, resolución, persistencia `pocketbiz.lang`, `html lang`, carga previa (`provideAppInitializer`), normalización de URL sin prefijo.
3. **Catálogos y paridad** (INV-03, AC-09, EDGE-04): `es/en/pt.json` con `COMMON`, `MENUITEMS`, `HEADER`; prueba de paridad; `provideTestTranslations()`; respaldo `es`.
4. **`app-language-selector`** + header + auth-layout (AC-01, AC-07, UI-01/03/05/06); quitar banderas y `de.json`; «Logout» a clave.
5. **Ola A**: sidebar, header, auth (signin/signup/forgot/reset/404/500), `shared`, `core` (mensajes). (AC-07, AC-08)
6. **Ola B — landing** (AC-06, UI-02): `landing-content.ts` a claves; selector en barra y menú móvil; CTA con prefijo.
7. **Ola C — features pequeñas**: settings, services, personnel, dentistry, agenda, customers, expenses. Un commit por feature con sus specs.
8. **Ola D — features grandes**: products, sales, purchases, inventory, reporting. Un commit por feature.
9. **Barrido de literales**: `grep` de tildes/ñ y palabras comunes en plantillas y TS no-spec para detectar texto restante; completar `en/pt`.
10. **Pruebas de integración de router** (AC-10, AC-11, EDGE-05/06) y ajuste de specs que comparan URLs.
11. **Docs**: `CLAUDE.md`; `npm test`, `npm run lint`, `npm run build` verdes.

## Database / migrations
No aplica.

## Risks
- **R-01** El `UrlSerializer` global puede chocar con el primer render o con `Location` (URL sin prefijo en la carga inicial, atrás/adelante). Mitigado por el paso 1 (PoC) y la alternativa documentada.
- **R-02** Volumen y omisiones de texto: mitigado por olas por feature, barrido de literales (paso 9) y revisión de `delivery-publish`.
- **R-03** Specs que afirman texto en español o URLs sin prefijo: helper `provideTestTranslations()` y ajuste puntual.
- **R-04** Calidad de las traducciones `en`/`pt` (redactadas por el agente): se declara en el PR; conviene revisión nativa.
- **R-05** Mensajes del backend en español (limitación, OQ-01).
- **R-06** Cadenas con pluralización o texto armado por concatenación: se migran a interpolación con parámetros; casos de plural usarán dos claves.

## New dependencies
Ninguna.

## Changelog
_(sin cambios; v1)_
