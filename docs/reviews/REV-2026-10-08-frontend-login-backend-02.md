# REV-2026-10-08-frontend-login-backend-02: Spec "logout without session does not call the API" no tiene expectativas de Jasmine

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-07-frontend-login-backend.md (v1)
**Spec reference:** AC-06 (logout), Test Specification › Unit tests (AuthService)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
El test solo usa `http.expectNone(...)` de `HttpTestingController`, que no cuenta como expectativa de Jasmine. Karma emite una advertencia y el spec no falla si el comportamiento cambia por una vía que no sea una petición HTTP (p. ej. si `logout()` dejara de limpiar la sesión).

## Expected behavior
Cada spec debe afirmar el resultado observable (aquí: emite `{success:false}`, `isAuthenticated` es `false`, sin petición).

## Actual behavior
```
WARN: 'Spec 'AuthService logout without session does not call the API' has no expectations.'
```

## Evidence
`src/app/core/service/auth.service.spec.ts` (spec `logout without session does not call the API`), salida de `ng test` con Chrome headless (18 specs, 18 SUCCESS, con esa advertencia).

## Required action
Añadir `expect` sobre el valor emitido y sobre `service.isAuthenticated`.
