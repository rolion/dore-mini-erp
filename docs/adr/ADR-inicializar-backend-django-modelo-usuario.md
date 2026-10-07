# ADR-inicializar-backend-django-modelo-usuario: Modelo de usuario propio desde la primera migración

**Estado:** Propuesto
**Task relacionado:** TASK-inicializar-backend-django
**Fecha:** 2026-10-05

## Contexto
`AUTH_USER_MODEL` no puede cambiarse de forma limpia una vez aplicada la primera migración que referencia `auth`. Hoy no hay usuarios ni datos, y `ddd.md` no define un módulo de identidad (los módulos son catalog, customers, sales, expenses, reporting). El esquema de autenticación de la API (sesión, token, JWT) tampoco está decidido ni es necesario para inicializar.

## Decisión
- Crear desde el inicio un modelo de usuario propio mínimo `User(AbstractUser)`, sin campos extra, en una app `modules/accounts` (solo `apps.py`, `models.py`, `migrations/`), y fijar `AUTH_USER_MODEL = "accounts.User"` antes de correr el primer `migrate`.
- `accounts` es infraestructura de identidad, no un bounded context de negocio: no tiene `domain/` ni `application/`, y ningún módulo de negocio lo importa directamente (si necesitan saber quién actúa, reciben un id).
- No se elige esquema de autenticación de la API todavía: `DEFAULT_AUTHENTICATION_CLASSES` queda en `SessionAuthentication` y `DEFAULT_PERMISSION_CLASSES` en `IsAuthenticated` (denegar por defecto); solo `/api/health/` es público. Token/JWT y permisos por rol se deciden en un task posterior cuando el frontend lo requiera.

## Alternativas consideradas
- **`auth.User` por defecto:** cero código, pero irreversible en la práctica si luego se necesita email como login u otros campos.
- **Modelo de usuario con email como `USERNAME_FIELD` ya:** anticipa un requerimiento no confirmado; se descarta por sobreingeniería (se puede añadir luego al modelo propio, que ya existe).
- **Diferir toda autenticación y no migrar:** deja el proyecto sin `migrate` utilizable y arriesga que el primer task con modelos fije `auth.User`.

## Estrategia de rollback / mitigación
Mientras no exista una base con datos, el rollback es borrar la base y revertir la migración inicial (`accounts/0001`) junto con el PR. Una vez aplicada en un entorno con datos reales, cambiar el modelo implica migración manual: por eso se decide ahora, con la base vacía. Denegar por defecto en DRF evita exponer endpoints sin querer.

## Consecuencias
- Fácil: añadir campos de usuario o cambiar el login más adelante vía migraciones normales.
- Difícil: hay una app más fuera de los 5 módulos de `ddd.md` (desviación mínima y documentada aquí; `docs/architecture/ddd.md` podría mencionarla en el plan).
- Pendiente consciente: esquema de autenticación de API, roles/permisos y CORS.
