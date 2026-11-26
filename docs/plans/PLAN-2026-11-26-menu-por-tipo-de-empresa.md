# PLAN-2026-11-26-menu-por-tipo-de-empresa (v1)

**Task:** TASK-menu-por-tipo-de-empresa · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-menu-por-tipo-de-empresa-selector-y-menu · ADR-menu-por-tipo-de-empresa-plantilla-inicial

## Objective
Al registrarse, la persona elige el tipo de empresa (compraventa, servicios u odontología). Ese tipo define los módulos con que nace la empresa y el orden del menú, sin limitar que el admin habilite más módulos después.

## Context
Hoy toda empresa nace con los 14 módulos y un menú de orden fijo. Ver TASK-menu-por-tipo-de-empresa.

# Specification

## Domain context
Contextos: `accounts` (alta de empresa), `modularity` (módulos por empresa), puerto `shared/company_defaults`. El frontend solo presenta.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Tipo de empresa | Plantilla elegida al registrarse: `compraventa`, `servicios`, `odontologia` (y `general` para las existentes) | ADR |
| Plantilla de módulos | Conjunto de módulos no base que se habilitan al crear la empresa | ADR |
| Diseño de menú | Orden y ubicación de los ítems del sidebar para un tipo | DDR |
| Presupuestos | Etiqueta del módulo Cotizaciones cuando se muestra dentro de Odontología | Chat 2026-11-26 |

## Current behavior
- Toda empresa recibe los 14 módulos del snapshot (`backend/shared/company_defaults/snapshot.json`; `backend/modules/modularity/infrastructure/defaults.py:27-47`).
- El registro no pide tipo (`backend/modules/accounts/api/serializers.py:11-17`).
- El menú tiene orden fijo (`frontend/panel_admin/src/assets/data/routes.json`).

## Expected behavior
- El registro exige un tipo de los tres públicos y lo guarda en la empresa.
- La empresa nace con los módulos de su plantilla y el resto de su configuración por defecto; el admin puede habilitar o deshabilitar módulos después como hoy.
- El menú se ordena según el tipo; un módulo apagado no aparece.
- Las empresas existentes quedan como `general` y su menú no cambia.

## Domain rules / invariants
- **INV-01 (nueva):** el tipo de una empresa lo fija el registro y no cambia después.
- **INV-02 (nueva):** las plantillas de módulos respetan las dependencias del catálogo (`requires`); un test lo comprueba por tipo.
- **INV-03 (nueva):** las plantillas son:
  - `compraventa`: `customers`, `sales`, `purchases`, `inventory`, `accounting`, `expenses`, `reporting`.
  - `servicios`: `services`, `personnel`, `agenda`, `customers`, `quotations`, `receivables`, `accounting`, `expenses`, `reporting`.
  - `odontologia`: las de `servicios` más `dentistry`.
  - `general`: los 14 módulos del snapshot.
  Los módulos base (`access`, `catalog`) siempre están.
- **INV-04 (existente):** toda consulta de negocio filtra por `company_id`; la empresa sale del usuario autenticado.

## Acceptance criteria
- **AC-01:** `POST /api/auth/register/` sin `company_type`, o con un valor fuera de `compraventa|servicios|odontologia` (incluido `general`), responde 400 con el error bajo `company_type` y no crea empresa ni usuario.
- **AC-02:** con un tipo válido crea la empresa con ese `company_type` y habilita exactamente los módulos de la plantilla (INV-03) más los base; `GET /api/modules/` lo refleja.
- **AC-03:** el resto de la configuración por defecto (cuentas, mapeos, categorías de gasto, almacén y ajustes) se aplica igual que hoy, en la misma transacción.
- **AC-04:** la respuesta de registro y de login incluye `user.company.type`.
- **AC-05:** el admin puede habilitar un módulo fuera de la plantilla (p. ej. `inventory` en una empresa de servicios) y deshabilitar uno de la plantilla, con las reglas de dependencia de hoy.
- **AC-06:** las empresas existentes quedan con tipo `general` tras la migración y conservan sus módulos.
- **AC-07:** `copy_company_defaults` sigue copiando los módulos del snapshot (sin perfil) igual que antes.
- **AC-08:** `/pocketbiz/signup` muestra el selector «Tipo de empresa» obligatorio con las tres opciones y su ayuda; sin elegir no envía y muestra el error; un error del servidor sobre `company_type` aparece bajo el campo.
- **AC-09:** el sidebar de cada tipo sigue el orden del DDR; Ajustes queda al final; un ítem de un módulo habilitado después y ausente del diseño aparece antes de Ajustes.
- **AC-10:** en `odontologia` «Presupuestos» es subítem de Odontología (después de Pacientes) y no existe «Cotizaciones» de primer nivel; si `quotations` está apagado, «Presupuestos» no aparece. En `servicios` y `compraventa` Cotizaciones es ítem propio.
- **AC-11:** con tipo `general`, ausente o desconocido (sesión guardada antes del cambio), el menú es idéntico al actual.
- **AC-12:** las claves nuevas existen en es/en/pt y `npm run i18n:check` pasa.

## Edge cases / Error cases
- **EDGE-01:** sesión guardada en el navegador sin `company.type`: se trata como `general`.
- **EDGE-02:** `company_type` con mayúsculas o espacios: se rechaza (valor exacto).
- **EDGE-03:** falla la aplicación de defaults: la transacción revierte la empresa (como hoy).
- **EDGE-04:** usuario sin empresa (`createsuperuser`): `company` es `null`, el menú usa el orden por defecto.

## Authorization / permissions
Registro público sin autenticación (como hoy). El tipo no concede ni quita permisos: el acceso a módulos lo controla el permiso de módulo de la API. El menú es presentación.

## API contract
- **API-01:** `POST /api/auth/register/` suma `company_type` (obligatorio, enum de tres valores). Cambio incompatible hacia atrás para clientes que no lo envíen; el único cliente es la SPA.
- **API-02:** `user.company` pasa de `{id, name}` a `{id, name, type}` en registro y login (compatible: campo añadido).

## UI behavior
- **UI-01:** campo de signup según DDR (plantilla «Autenticación»), `form-select` con `label`, ayuda variable y texto de apoyo.
- **UI-02:** sidebar con el orden del DDR y la regla de «Presupuestos».

## Non-functional requirements
Sin consultas adicionales por petición: el tipo viaja en el usuario ya cargado. La reordenación del menú es una función pura sin acceso a red.

## Out of scope
- Cambiar el tipo después del registro.
- Ocultar «Productos» del catálogo por tipo.
- Un cuarto tipo público o un tipo «personalizado».
- Reclasificar empresas existentes.
- Cambios al catálogo de módulos o a sus dependencias.

## Open questions
- Si se quiere ofrecer «Otro / completo» (los 14 módulos) en el registro: hoy `general` es solo para empresas existentes. No bloquea.

# Test Specification

## Unit tests
- Dominio: cada plantilla cumple `requires` (INV-02), solo contiene claves del catálogo y no incluye módulos base.
- Frontend: `arrangeRoutes` por tipo (orden, anidado de Presupuestos, leftovers antes de Ajustes, tipo desconocido).
- Frontend: componente signup (campo obligatorio, ayuda, error de servidor).

## Integration tests
- Registro por API con cada tipo: módulos habilitados exactos, configuración por defecto aplicada, `company.type` en la respuesta.
- Registro con tipo ausente, inválido o `general`: 400 y nada creado.
- Habilitar y deshabilitar un módulo fuera de la plantilla después del alta.
- Migración `0003`: empresas existentes quedan en `general` (`test_migrations.py`).
- `copy_company_defaults` y `apply_all` sin perfil mantienen los 14 módulos.
- Paridad entre `CompanyType` de `accounts` y las plantillas de `modularity`.

## E2E
**NO** — el flujo se cubre con integración de API y pruebas de componentes; no es un flujo crítico de punta a punta nuevo.

## Regression tests
`sidebar-menu.spec.ts` (se actualiza por el campo `id`), `signup.component.spec.ts`, `test_company_defaults.py`, `tests.py` de accounts.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Integración: registro con tipo ausente, inválido y `general` |
| AC-02 | Integración por tipo + unit de plantillas |
| AC-03 | Integración: secciones de defaults presentes tras el alta (reutiliza `test_company_defaults.py`) |
| AC-04 | Integración: respuesta de registro y de login |
| AC-05 | Integración: habilitar/deshabilitar tras el alta |
| AC-06 | Migración (`test_migrations.py`) |
| AC-07 | Integración de `copy_company_defaults` |
| AC-08 | Componente signup |
| AC-09 | Unit de `arrangeRoutes` + `sidebar-menu.spec.ts` |
| AC-10 | Unit de `arrangeRoutes` con y sin `quotations` |
| AC-11 | Unit de `arrangeRoutes` (general, ausente, desconocido) |
| AC-12 | `npm run i18n:check` + prueba de paridad de claves |

# Implementation Plan

## Architecture considerations
Ver el ADR. Resumen: `Company.company_type` + plantillas en `modularity/domain` + parámetro `profile` en el puerto de defaults + `arrangeRoutes` en el frontend.

## Proposed solution
El tipo viaja del formulario al registro, se guarda, selecciona la plantilla de módulos vía `profile` y vuelve en `user.company.type` para que el sidebar reordene `routes.json`.

## Files/components affected
- **Backend:** `modules/accounts/models.py` (+ `CompanyType`, campo), migración `accounts/0003_company_type.py` (nueva), `accounts/registration.py`, `accounts/api/serializers.py`, `accounts/api/views.py`; `shared/company_defaults/__init__.py` (`profile`); `modules/modularity/domain/company_types.py` (nuevo), `modularity/infrastructure/defaults.py`; tests en `accounts` y `modularity`; `accounts/admin.py` (mostrar el tipo en solo lectura).
- **Frontend:** `core/models/user.ts`, `core/service/auth.service.ts` (+ mapeo del campo), `authentication/signup/*`, `layout/sidebar/` (`sidebar.metadata.ts` + `id`, `menu-layout.ts` nuevo, `sidebar.component.ts`), `assets/data/routes.json` (+ `id` por ítem), `assets/i18n/{es,en,pt}.json`, specs.
- **Docs:** `CLAUDE.md` (registro con tipo), `docs/design/design-system.md` (sección 6).

## Implementation steps
1. **Backend dominio:** `company_types.py` con las plantillas (INV-03) y test de dependencias. (INV-02, INV-03)
2. **Modelo y migración:** `CompanyType`, campo `company_type` con `default='general'`, migración `0003`, test de migración. (AC-06, INV-01)
3. **Puerto de defaults:** `apply_all(..., profile=None)` publica `ctx['profile']`; `apply_modularity` usa la plantilla si hay perfil. (AC-02, AC-07)
4. **Registro y API:** serializer con `company_type`, `register_company_admin` lo guarda y pasa `profile`; `UserSerializer.company.type`; tests de integración. (AC-01..AC-05)
5. **Frontend modelo y servicio:** `UserCompany.type`, `RegisterInput.companyType` y su mapeo a `company_type`. (AC-04, AC-08)
6. **Signup:** selector, ayuda variable, validación, errores de servidor, claves i18n es/en/pt y spec. (AC-08, AC-12)
7. **Menú:** `id` en cada ítem de `routes.json`; `arrangeRoutes` y diseños por tipo en `menu-layout.ts`; integrarlo en `SidebarComponent` antes de `visibleRoutes`; clave i18n «Presupuestos»; specs. (AC-09..AC-11)
8. **Documentación:** `CLAUDE.md` y `design-system.md`.
9. **Verificación:** `python manage.py test`, ruff/flake8 sobre lo cambiado, `npm test`, `npm run lint`, `npm run i18n:check`, `npm run build`.

## Database / migrations
Una migración nueva `accounts/0003_company_type` (`AddField`, `CharField(max_length=20, default='general')`). No se edita ninguna migración aplicada. Rollback: `migrate accounts 0002`.

## Risks
- Defaults de módulos apagados aplicados a empresas que no los usan: se verifica que habilitar el módulo después es idempotente.
- Orden de aplicación en el alta: `apply_modularity` va al final (`ORDER = 70`), así los ganchos de ciclo de vida de los módulos de la plantilla encuentran su configuración.
- Sesiones guardadas sin `company.type`: cubiertas por EDGE-01.

## New dependencies
Ninguna.
