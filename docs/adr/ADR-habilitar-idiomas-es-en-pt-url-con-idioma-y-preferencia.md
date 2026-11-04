# ADR-habilitar-idiomas-es-en-pt-url-con-idioma-y-preferencia: URL con prefijo de idioma y preferencia guardada

**Estado:** Propuesto
**Task relacionado:** TASK-habilitar-idiomas-es-en-pt
**Fecha:** 2026-11-03

## Contexto
La URL debe reflejar el idioma y la elección debe guardarse en el navegador (por defecto español). Hechos: la landing vive en `/` y el producto en `/pocketbiz/**` (`app.routes.ts:13-20`); hay 311 referencias absolutas a `/pocketbiz` en 153 archivos no-spec (routerLink/navigate) y 27 usos de `APP_BASE`/`APP_PATHS`; existen redirecciones de URLs antiguas (`core/routing/legacy-redirects.ts`) y de `/#/…`; la preferencia actual se guarda con prefijo de tema (`storage.service.ts:19-27`).

## Decisión
1. **Esquema de URL: prefijo de idioma**: `/es`, `/en`, `/pt` delante de la ruta actual. Ejemplos: `/es` (landing), `/en/pocketbiz/login`, `/pt/pocketbiz/sales/orders/12?x=1`. Los códigos son ISO 639-1; la etiqueta visible (Spa/En/Pr) es independiente.
2. **Sin tocar las 311 referencias**: un `UrlSerializer` propio (extiende `DefaultUrlSerializer`, registrado con `{provide: UrlSerializer, useClass: ...}`):
   - `parse(url)`: si el primer segmento es `es|en|pt`, lo **quita** y registra el idioma pedido por la URL; el árbol de rutas del router queda **idéntico al actual** (sin prefijo). Si no hay prefijo, se parsea tal cual.
   - `serialize(tree)`: **antepone** el idioma activo a toda URL generada (`routerLink`, `navigate`, redirects, `Location`).
   Así `app.routes.ts`, `LEGACY_REDIRECTS`, guards y las 311 referencias no cambian.
3. **Resolución del idioma (precedencia)**: (a) prefijo de la URL, si existe; (b) preferencia guardada en el navegador; (c) `es`. Una URL sin prefijo (`/`, `/pocketbiz/login`, marcadores antiguos) se normaliza **reemplazando** la entrada del historial por la versión con prefijo (`/es/…` o el idioma guardado), conservando ruta, query y fragmento.
4. **Persistencia**: solo cuando la persona **elige** un idioma en el selector se guarda (`localStorage`, clave propia `pocketbiz.lang`, **sin** prefijo de tema, envuelta en `try/catch` por si el almacenamiento falla). Abrir un enlace `/en/…` aplica inglés en esa sesión pero **no sobrescribe** la preferencia guardada. Valores no válidos (p. ej. `de` de la clave antigua) se ignoran. No se usa el idioma del navegador (ya decidido en `language.service.ts:18`).
5. **Cambio de idioma en caliente**: `LanguageService.setLanguage(lang)` carga el catálogo, y recién entonces actualiza el idioma activo, guarda la preferencia y reescribe la barra de direcciones con la **misma ruta y otro prefijo** (`Location.replaceState` con `router.url` re-serializado; no hay navegación del router, por lo que no se recargan componentes ni se disparan guards; el pipe `translate` es reactivo y repinta solo). Actualiza `document.documentElement.lang`.
6. **Idioma inválido en la URL** (`/fr/…`): no es prefijo reconocido; se trata como ruta sin prefijo y cae en la 404 existente, que se muestra en el idioma activo.
7. **Despliegue**: sin cambios; `/es|en|pt/**` son rutas de SPA y el servidor ya devuelve `index.html` para todo lo que no sea `/api/*`, `/admin/*` o estático (`CLAUDE.md`). `/api` y `/admin` nunca llevan prefijo.
8. **Landing**: `/` pasa a `/es` (y `/en`, `/pt`). `APP_PATHS.landing` sigue siendo `'/'` en el código; el serializer produce `/<lang>`.

## Alternativas consideradas
- **Ruta padre `:lang` con todos los hijos** (`/:lang/pocketbiz/...`): es lo más explícito en Angular, pero obliga a reescribir `APP_BASE`/`APP_PATHS` y 311 referencias (o a inyectar el idioma en cada `routerLink`), y a mantener las redirecciones antiguas por duplicado. Mayor riesgo y diff, mismo resultado visible. Descartada. Queda como respaldo si la prueba de concepto del serializer (primer paso del plan) revela un límite de Angular.
- **Query param `?lang=en`**: trivial, pero no es una URL «con idioma» limpia, se pierde en cada navegación interna y es peor para compartir/SEO. Descartada.
- **Subdominios o builds por locale** (Angular i18n compile-time): una build por idioma, sin cambio en caliente; incompatible con el selector instantáneo. Descartada.
- **Guardar la preferencia en el backend (perfil)**: el requerimiento pide guardarla en el explorador; el backend y la landing pública no tienen perfil. Descartada.
- **Usar `Accept-Language`/idioma del navegador como valor por defecto**: el requerimiento fija español por defecto. Descartada.

## Estrategia de rollback / mitigación
- Cambio localizado: `UrlSerializer`, `LanguageService`, normalización inicial y selector. Revertir el PR restaura las URLs sin prefijo. Mientras exista el serializer, **las URLs sin prefijo siguen funcionando** (marcadores y enlaces antiguos no se rompen).
- Tras un rollback, los enlaces compartidos `/es/…` caerían en 404; es aceptable porque la funcionalidad es nueva y no hay enlaces previos con prefijo.
- Primer paso del plan = prueba de concepto del serializer con las rutas reales (landing, login, una ruta profunda con parámetros, recarga, atrás/adelante, `/#/…` heredado, redirects legacy). Si falla, se pasa a la alternativa de ruta padre `:lang` mediante `PLAN_UPDATE_REQUIRED`.
- Sin migraciones ni datos persistentes del servidor.

## Consecuencias
- **Más fácil:** URLs compartibles por idioma; 0 cambios en las 311 referencias y en las rutas; la landing y el panel cambian de idioma sin recargar.
- **Más difícil:** un `UrlSerializer` global es «magia» transversal: hay que documentarlo y probarlo; cualquier enlace construido como string fuera del router (`window.location`, `<a href>`) debe pasar por el router. Pruebas que comparan `router.url`/`Location.path()` deberán esperar el prefijo.
- **Deuda aceptada:** el prefijo `es` aparece siempre (no hay «español sin prefijo»), por simetría y por el requisito «la URL refleja el lenguaje seleccionado».
