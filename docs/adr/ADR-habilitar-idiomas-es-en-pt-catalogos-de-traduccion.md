# ADR-habilitar-idiomas-es-en-pt-catalogos-de-traduccion: Catálogos de traducción por clave en toda la interfaz

**Estado:** Propuesto
**Task relacionado:** TASK-habilitar-idiomas-es-en-pt
**Fecha:** 2026-11-03

## Contexto
`ngx-translate` está instalado y configurado, pero solo el menú lateral lo usa (`sidebar.component.html:32-79`); `assets/i18n/*.json` contiene únicamente `MENUITEMS`. El resto del texto está hardcodeado en español en ~72 plantillas de `features/`, ~75 archivos TS y la landing (`landing-content.ts`). El idioma se carga de forma asíncrona sin inicializador (`app.config.ts:23-29`).

## Decisión
1. **Se mantiene `ngx-translate`** (sin dependencias nuevas). Idiomas soportados: `es` (referencia y respaldo), `en`, `pt`. Se elimina `de.json` y el idioma `de`.
2. **Un catálogo JSON por idioma**: `assets/i18n/{es,en,pt}.json`, **claves anidadas por área**, en MAYÚSCULAS como las actuales de `MENUITEMS`: `COMMON.*` (acciones y estados compartidos: Guardar, Cancelar, Cargando…), `MENUITEMS.*`, `HEADER.*`, `AUTH.*`, `LANDING.*`, `<FEATURE>.*` (`PRODUCTS`, `CUSTOMERS`, `SALES`, `EXPENSES`, `REPORTING`, `PURCHASES`, `INVENTORY`, `SERVICES`, `PERSONNEL`, `DENTISTRY`, `AGENDA`, `SETTINGS`, `ERRORS`). Un archivo por idioma (no uno por feature) para mantener una sola carga HTTP y paridad fácil de verificar.
3. **Uso en plantillas:** pipe `translate` (`{{ 'PRODUCTS.LIST.TITLE' | translate }}`) y parámetros con `{{ 'X' | translate: { count: n } }}` con interpolación `{{count}}`. Atributos (`placeholder`, `aria-label`, `title`) con `[attr]="'KEY' | translate"`. **Sin texto visible hardcodeado**.
4. **Uso en TypeScript:** constantes con texto visible (p. ej. `landing-content.ts`, etiquetas de estado, mensajes de error del frontend, toasts) pasan a **claves** (la constante guarda la clave y la plantilla la traduce) o, si el texto se arma en código, a `TranslateService.instant/stream`. Los modelos de dominio del frontend no conservan texto traducido.
5. **Carga previa al render:** `provideAppInitializer` carga el catálogo del idioma resuelto (ver ADR de URL) antes de pintar, para evitar claves o texto en el idioma equivocado. Respaldo `defaultLanguage: 'es'` con `useDefaultLang`: una clave faltante en `en`/`pt` muestra el español, **no** la clave.
6. **Paridad verificada por prueba:** una prueba unitaria compara `es.json`, `en.json` y `pt.json` y falla si el conjunto de claves difiere o si hay valores vacíos o con interpolaciones distintas (`{{x}}`). Garantiza que una clave nueva no se olvide en un idioma.
7. **Pruebas de componentes:** un helper de pruebas `provideTestTranslations()` (carga `es.json` de forma síncrona) para que las specs sigan afirmando textos en español sin repetir configuración.
8. **Fuera del catálogo:** datos del usuario, nombres de módulos que llegan del backend con su propio texto (se evaluará en el plan si `modules.service` devuelve claves o nombres — se mapea por clave del módulo en el frontend), mensajes del backend (limitación declarada), páginas de demostración Oreva no enlazadas desde el menú.
9. **Formatos:** fechas y montos conservan su formato actual (`dd/MM/yyyy`); sin `LOCALE_ID` por idioma.

## Alternativas consideradas
- **i18n nativo de Angular (`$localize`, build por locale):** cambio de idioma requiere otro bundle y URL/servidor por locale; sin cambio en caliente. Descartada.
- **Un JSON por feature con carga diferida:** menos bytes iniciales, pero 3 × 13 archivos, múltiples cargas y más complejidad de paridad; el catálogo total (~unos cientos de claves por idioma) es pequeño. Descartada (YAGNI); revisable si el catálogo crece.
- **Claves en inglés/dot.case (`products.list.title`)**: más convencional, pero rompe la convención existente (`MENUITEMS.DASHBOARD.TEXT`). Se mantiene la convención actual.
- **Traducir en el backend (API devuelve texto por `Accept-Language`):** cubre los mensajes de error, pero es otra capacidad (cambios de API y catálogos `.po`, ~190 mensajes). Queda como seguimiento propuesto.
- **Herramienta de extracción automática de textos:** requeriría nueva dependencia; la extracción se hace manualmente por módulo con la prueba de paridad como red de seguridad.

## Estrategia de rollback / mitigación
- Cambio aditivo: las claves nuevas se agregan junto al texto; se migra feature por feature en commits separados dentro del mismo PR, cada uno compilando y con pruebas verdes. Revertir un commit devuelve esa feature al texto hardcodeado.
- El respaldo en español evita pantallas con claves visibles si falta una traducción; la prueba de paridad evita llegar a esa situación.
- Sin migraciones ni cambios en el servidor.

## Consecuencias
- **Más fácil:** añadir un idioma = un JSON más + registrarlo en `SUPPORTED_LANGUAGES`; los textos quedan centralizados y revisables por una persona de negocio.
- **Más difícil:** todo texto nuevo exige claves en los tres idiomas; los specs que afirman texto necesitan el helper de traducciones; cambio grande en el diff (~150 plantillas + ~75 TS).
- **Deuda aceptada:** mensajes del backend en español; formatos de fecha/número sin localizar; traducciones en/pt redactadas por el agente (conviene revisión nativa).
