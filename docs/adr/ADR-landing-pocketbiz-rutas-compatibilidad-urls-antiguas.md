# ADR-landing-pocketbiz-rutas-compatibilidad-urls-antiguas: Redirecciones de URLs anteriores a `/pocketbiz`

**Estado:** Propuesto
**Task relacionado:** TASK-landing-pocketbiz-rutas
**Fecha:** 2026-10-13

## Contexto
Al mover el producto bajo `/pocketbiz` (ver `ADR-landing-pocketbiz-rutas-esquema-rutas-montaje`), las URLs actuales (`/authentication/signin`, `/dashboard/main`, `/sales/orders`, …) dejarían de existir. La investigación del task marca como hipótesis no confirmada si deben redirigir, y el DDR fija la expectativa de UX: **quien tenga un marcador no debe ver un 404**. Además, con ≈ 140 enlaces absolutos por actualizar, un enlace olvidado también se traduciría en un 404.

Hechos: el producto está "en construcción" (`CLAUDE.md`), el equipo de usuarios es pequeño y la sesión vive en `localStorage` independiente de la ruta; no hay consumidores externos de las URLs del cliente (la API `/api` no cambia).

## Decisión
Agregar, en `app.routes.ts` y **antes** de `**`, un conjunto **explícito y acotado** de redirecciones de compatibilidad, conservando subruta y parámetros de consulta:

| URL antigua | Destino |
|---|---|
| `/authentication/signin` | `/pocketbiz/login` |
| `/authentication/signup` | `/pocketbiz/signup` |
| `/authentication/forgot`, `/reset`, `/page404`, `/page500` | `/pocketbiz/forgot`, `/reset`, `/page404`, `/page500` |
| `/dashboard/**`, `/catalog/**`, `/customers/**`, `/sales/**`, `/expenses/**`, `/reports/**` | `/pocketbiz/<misma ruta>` |

Reglas:
- Se implementan con `redirectTo` en forma de función (disponible en Angular 21), que reconstruye la URL con `APP_BASE` y los segmentos originales.
- **Solo** los prefijos listados (negocio y autenticación). Las rutas de páginas demo de la plantilla **no** se redirigen: cualquier otra ruta desconocida cae en `**` → `Page404Component`.
- El destino pasa después por `AuthGuard` (sin sesión → `/pocketbiz/login`).
- Las redirecciones son **temporales**: se documentan con un comentario y una nota en el task para retirarlas cuando no haya marcadores relevantes. No se fija fecha porque depende de la adopción.
- La raíz `/` **no** redirige: carga la landing, incluso con sesión activa (decisión del DDR).

## Alternativas consideradas
- **Sin redirecciones.** Más simple y sin deuda, pero cualquier marcador o enlace olvidado da 404. Aceptable solo si no hubiera usuarios; con un producto en uso real es una regresión visible. Descartada.
- **Redirección universal** (`**` → `/pocketbiz/<url>`). Cubre todo con una regla, pero convierte cualquier error de tipeo en una redirección al panel/login y oculta enlaces rotos reales. Descartada.
- **Redirección en servidor** (301 en proxy/nginx). Correcta para SEO, pero el repo no tiene configuración de servidor y acoplaría el comportamiento a un despliegue no definido. Se deja como mejora si aparece infraestructura propia.

## Estrategia de rollback / mitigación
- Aditivo y sin efectos en datos: retirar las redirecciones es borrar su bloque en `app.routes.ts`.
- Riesgo de bucle: ningún destino coincide con un origen (todos terminan en `pocketbiz/…`); un spec de rutas debe comprobar la tabla anterior y la ausencia de ciclos (`/authentication/signin` → `/pocketbiz/login`, no a sí mismo).
- La redirección no cambia la autorización: sigue mandando el guard del cliente y el servidor (token, `CompanyAdminPermission`).

## Consecuencias
- **Más fácil:** los marcadores y cualquier enlace aún no actualizado siguen funcionando; la migración de rutas puede revisarse sin urgencia.
- **Más difícil:** hay una tabla pequeña que mantener y retirar; los specs que verifican rutas literales deben cubrir también estas redirecciones.
- **Deuda aceptada:** las redirecciones del cliente no transmiten un 301 a buscadores ni a clientes no-navegador; es suficiente porque la antigua URL pública del producto no estaba indexada (era una pantalla de login).
