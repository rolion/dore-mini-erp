# REV-2026-10-08-frontend-login-backend-01: El proxy de `ng serve` apunta a `localhost:8000` y no alcanza al backend de `runserver`

**Status:** Closed (verificado en re-review 2026-10-08)
**Severity:** High
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-10-07-frontend-login-backend.md (v1)
**Spec reference:** AC-03 (login válido entra al dashboard), AC-04 (mensaje de credenciales inválidas), Expected behavior, ADR decisión 3 (proxy de desarrollo sin CORS)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-plan

## Description
El paso 5 del Implementation Plan fija el target del proxy en `http://localhost:8000` y `frontend/panel_admin/proxy.conf.json` lo implementa literalmente. En Node 22 sobre Windows, `localhost` se resuelve primero a `::1` (IPv6), mientras que `python manage.py runserver` (comando documentado en `CLAUDE.md`) escucha solo en `127.0.0.1`. El proxy de Vite recibe `ECONNREFUSED ::1:8000` y responde 500 a toda petición `/api/*`.

Consecuencia: siguiendo el procedimiento documentado (`runserver` + `npm start`) **ningún** login funciona: ni el válido (AC-03) ni el inválido (AC-04, que muestra "No se pudo conectar con el servidor" en vez de "Credenciales inválidas").

## Expected behavior
Spec: "El formulario de login valida usuario/contraseña contra el backend"; AC-03: credenciales válidas → entra a `/dashboard/main`; AC-04: inválidas → "Credenciales inválidas". ADR decisión 3: `ng serve` hace proxy de `/api` al backend.

## Actual behavior
Con `runserver` en `127.0.0.1:8000` y `ng serve` con la configuración del repo, `POST http://localhost:4200/api/auth/login/` → 500 y el formulario muestra el mensaje de error de conexión. Con el target cambiado a `http://127.0.0.1:8000` (proxy temporal fuera del repo) el smoke completo pasa (login inválido → "Credenciales inválidas"; válido → `#/dashboard/main`; logout → signin y el token antiguo da 401).

## Evidence
Log de `ng serve` (config del repo):
```
8:54:33 AM [vite] http proxy error: /api/auth/login/
Error: connect ECONNREFUSED ::1:8000
```
Red en el navegador y `curl`:
```
POST http://localhost:4200/api/auth/login/ → 500 Internal Server Error
$ curl -i -X POST localhost:4200/api/auth/login/ ...   → HTTP/1.1 500 Internal Server Error
```
Backend directo (sí responde): `curl -X POST localhost:8000/api/auth/login/ -d '{"username":"smoke","password":"bad"}'` → `401 {"detail":"Credenciales inválidas."}`.

## Required action
Actualizar el PLAN (paso 5) para que el target sea `http://127.0.0.1:8000` (o, alternativamente, documentar `runserver` con bind dual-stack), aplicar el cambio en `proxy.conf.json` y actualizar la nota de `CLAUDE.md`/PR ("proxy ... a `localhost:8000`").
