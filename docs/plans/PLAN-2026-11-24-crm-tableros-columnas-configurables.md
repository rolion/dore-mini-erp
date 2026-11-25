# PLAN-2026-11-24-crm-tableros-columnas-configurables (v1)

**Task:** TASK-crm-tableros-columnas-configurables · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-crm-tableros-columnas-configurables-editor-de-etapas.md` · `docs/adr/ADR-crm-tableros-columnas-configurables-modelo-y-puerto-de-tarjetas.md`

## Objective
Permitir que el administrador cree y gestione tableros comerciales con etapas ordenables, renombrables y archivables, preservando las tarjetas al archivar una etapa (reasignación obligatoria a otra etapa) y dejando a cada empresa con un tablero «Ventas» base.

## Context
Historia PB-CRM-003 (Trello, ver TASK). Decisiones del usuario: base `crm`; el tablero «Ventas» automático y los nuevos tableros nacen sin etapas; Karma en lugar de Playwright. Habilita PB-CRM-004.

# Specification

## Domain context
Bounded context `crm` (lectura+escritura desde esta tarea). Contextos relacionados: `modularity` (solo `required_modules`), `shared.company_defaults`. Sin dependencias nuevas hacia otros módulos.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Tablero (`CRMBoard`) | Conjunto ordenado de etapas comerciales de una empresa | tarjeta Trello |
| Etapa (`CRMStage`) | Columna del tablero por la que avanzan las tarjetas | tarjeta Trello |
| Archivar | Marcar `is_active=false`; nunca se borra | tarjeta Trello |
| Tarjeta | Oportunidad ubicada en una etapa (la crea PB-CRM-004) | tarjeta Trello |
| Posición | Entero 1..n contiguo entre etapas activas del tablero | ADR |

## Current behavior
No existe ningún concepto de tablero ni etapa (ver TASK, «Comportamiento actual»). Permisos: toda la API exige admin de empresa activa (`config/permissions.py:19`, `accounts/api/permissions.py:12-21`).

## Expected behavior
Cada empresa tiene un tablero «Ventas» sin etapas tras registrarse. El admin puede crear tableros adicionales, renombrarlos, archivarlos y reactivarlos; dentro de un tablero crea, renombra, reordena y archiva etapas. El orden persiste. Archivar una etapa con tarjetas exige una etapa destino y mueve todas las tarjetas en la misma transacción.

## Domain rules / invariants
- INV-01 (nueva): nombres de tablero únicos por empresa, sin distinguir mayúsculas, entre tableros activos; nombres de etapa únicos por tablero, ídem entre etapas activas. Nombre recortado, 1-80 caracteres.
- INV-02 (nueva): las posiciones de las etapas activas de un tablero son 1..n contiguas y sin repetir; agregar añade al final; archivar recompacta.
- INV-03 (nueva): una etapa archivada no recibe tarjetas ni se puede renombrar/reordenar; la etapa destino de una reasignación debe ser activa, del mismo tablero y distinta de la archivada.
- INV-04 (nueva): reordenar exige la lista completa y exacta de ids de etapas activas del tablero (sin faltantes, repetidos ni ajenos).
- INV-05 (nueva): archivar una etapa con tarjetas sin destino válido, o un tablero con tarjetas, no cambia nada (409).
- INV-06 (existente): todo dato se filtra por `company_id` del usuario autenticado; ids ajenos → 404.

## Acceptance criteria
- AC-01: al registrarse una empresa (y al `copy_company_defaults`) existe un tablero activo «Ventas» sin etapas; repetir la copia no lo duplica.
- AC-02: el admin crea un tablero con nombre (nace sin etapas); un nombre duplicado entre activos → 400; puede renombrarlo, archivarlo y reactivarlo.
- AC-03: el admin agrega una etapa (queda al final), la renombra y la lista de etapas activas viene ordenada por posición.
- AC-04: reordenar con la lista completa persiste el nuevo orden tras recargar; una lista incompleta, repetida o con ids ajenos/archivados → 400/409 sin cambios.
- AC-05: archivar una etapa sin tarjetas la oculta de la lista activa y recompacta posiciones.
- AC-06: archivar una etapa con tarjetas sin `target_stage_id` → 409 `stage_has_cards` con la cantidad; con destino válido mueve todas las tarjetas y archiva en una transacción; si falla, nada cambia.
- AC-07: un tablero con tarjetas no se puede archivar (409 `board_has_cards`).
- AC-08: ids de tablero/etapa de otra empresa (en ruta o en `target_stage_id`) → 404; un usuario sin empresa activa o no admin → 403; sin sesión → 401.
- AC-09: UI «CRM → Tablero»: selector de tablero, crear/renombrar tablero, crear/renombrar/subir/bajar/archivar etapa, diálogo de destino cuando hay tarjetas, estados vacío/cargando/error, recarga conserva el orden.

## Edge cases / Error cases
Tablero sin etapas; archivar la única etapa; reactivar tablero cuyo nombre ya usa uno activo (409/400); dos admins reordenando a la vez (el segundo recibe 409 `stage_order_stale` y recarga); etapa destino igual a la archivada o archivada; nombre solo con espacios.

## Authorization / permissions
Único rol `admin` (`UserRole.ADMIN`), ya exigido por el permiso por defecto; `required_modules = ('customers',)`. La empresa sale de `shared/tenancy.company_id_from`.

## API contract
Base `/api/crm/boards/`. Compatibilidad: nuevo, sin cambios en endpoints existentes.
- API-01 `GET /` lista tableros `?active=true|false|` (por defecto activos y archivados con `is_active`): `[{id, name, is_active, stages: [{id, name, position, is_active, card_count}]}]` (solo etapas activas, ordenadas por `position`; `card_count` = 0 hasta PB-CRM-004). `POST /` `{name}` → 201.
- API-02 `GET/PATCH /<board_id>/` (`{name}`); `POST /<board_id>/archive/` y `/reactivate/`.
- API-03 `POST /<board_id>/stages/` `{name}` → 201 (al final).
- API-04 `PATCH /<board_id>/stages/<stage_id>/` `{name}`.
- API-05 `PUT /<board_id>/stages/order/` `{stage_ids: [uuid…]}` → tablero actualizado.
- API-06 `POST /<board_id>/stages/<stage_id>/archive/` `{target_stage_id?}` → tablero actualizado; 409 `stage_has_cards` (`card_count`), 400 destino inválido.
- Errores: `{detail|field: [mensajes]}` como el resto de la API; códigos 409 con clave `code`.

## UI behavior
- UI-01: Menú CRM → Tablero, ruta `/pocketbiz/crm/board`, `moduleGuard` de `customers`.
- UI-02: plantilla «Editor de lista ordenable con botones Subir/Bajar» (DDR; `design-system.md` §5): selector «Tablero», tabla Orden/Nombre/Acciones, alta de etapa al pie.
- UI-03: guardado inmediato por acción; tras cada respuesta la lista se reemplaza por el estado del servidor.
- UI-04: diálogo «Archivar etapa»: sin tarjetas confirmación simple; con tarjetas, selector de destino obligatorio.
- UI-05: estados vacío/cargando/error/409 según DDR; botones de icono con `title` y `aria-label`; todo texto con claves i18n es/en/pt.

## Non-functional requirements
Operaciones de escritura atómicas con bloqueo de fila del tablero; listados sin N+1 (una consulta de etapas por página de tableros); accesible por teclado.

## Out of scope
Tarjetas/oportunidades y su vista Kanban (PB-CRM-004), segmentos, permisos por rol adicional, arrastrar y soltar, clave de módulo `crm`, eliminar físicamente, Playwright.

## Open questions
- PB-CRM-004 debe implementar `StageCards` (puerto) con conteo y reasignación reales; sin bloqueo para esta tarea.

# Test Specification

## Unit tests
Dominio puro (`crm/tests/test_domain.py`): INV-01…INV-05 (nombres, posiciones contiguas, reorder exacto, archivar con/sin destino, destino inválido).

## Integration tests
API (`crm/tests/test_api_boards.py`) con `StageCards` falso inyectable: AC-02…AC-08, orden persistente tras relectura, atomicidad (el falso falla a mitad → nada cambia), aislamiento entre dos empresas, 401/403, validación de `page`/`active`. Defaults (`test_defaults.py`): AC-01 e idempotencia. Migración: `makemigrations --check`. `test_boundaries.py` actualizado.
Frontend (Karma): servicio API (URLs y cuerpos), componente `crm-board` (selector, alta/renombrado/subir/bajar/archivar, diálogo con destino, estados vacío/error/409, recarga), `sidebar-menu.spec.ts`, paridad y uso de claves i18n.

## E2E
**NO** — la tarjeta pide Playwright, pero el repo no lo tiene y instalarlo es una dependencia nueva; el usuario eligió Karma. «Recargar y conservar el orden» se cubre con la API (relectura) y con la prueba de componente que vuelve a cargar desde el servicio simulado.

## Regression tests
Suite de `config` (settings/urls) y de `company_defaults` (snapshot con nueva sección), `i18n:check`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | `test_defaults.py`; test de registro de empresa |
| AC-02 | API boards (crear/duplicado/renombrar/archivar/reactivar) |
| AC-03 | API stages + dominio |
| AC-04 | API order (completo, incompleto, ajeno) + relectura |
| AC-05 | API archive sin tarjetas + dominio (recompactado) |
| AC-06 | API archive con puerto falso (409, destino válido, falla atómica) |
| AC-07 | API archive tablero con puerto falso |
| AC-08 | API: empresa B → 404, no admin/sin empresa → 403, sin token → 401 |
| AC-09 | Karma componente + servicio + menú |

# Implementation Plan

## Architecture considerations
Ver ADR: dominio puro (`Board`), casos de uso en `application/` con repositorio y puerto `StageCards`, adaptador nulo hoy. Bloqueo `select_for_update` del tablero en toda escritura.

## Proposed solution
Agregado `Board` con etapas; repositorio Django por empresa; casos de uso `CreateBoard`, `RenameBoard`, `ArchiveBoard`, `ReactivateBoard`, `AddStage`, `RenameStage`, `ReorderStages`, `ArchiveStage`; vistas DRF finas; sección de defaults; pantalla Angular con servicio inyectable y Reactive Forms.

## Files/components affected
- Backend: `backend/modules/crm/` (`apps.py`, `domain/board.py`, `application/{ports,services}.py`, `infrastructure/django/{models,repositories}.py`, `infrastructure/{adapters,defaults}.py`, `api/{serializers,views,urls}.py`, `migrations/0001_initial.py`, `tests/`), `config/settings/base.py` (INSTALLED_APPS), `config/urls.py` (`api/crm/boards/`; si existe `api/crm/`, incluir bajo él), `shared/company_defaults/snapshot.json`, registro de defaults (donde se llama `register()`), `modules/sales/tests/test_boundaries.py` (si el mapa lo exige), `docs/architecture/ddd.md`.
- Frontend: `features/crm/` (`crm.routes.ts`, `pages/crm-board`, `components/archive-stage-dialog`, `services/crm-boards.service.ts`, `models/board.ts`, `testing/`), `app.routes.ts`, `assets/data/routes.json`, `assets/i18n/{es,en,pt}.json`, `sidebar-menu.spec.ts`.
- Migraciones: `crm 0001_initial` (tablas `crm_board`, `crm_stage`, restricciones únicas condicionales). Si el PR 120 aporta migraciones de `crm`, la numeración se ajusta al rebasar; nunca se edita una migración aplicada.
- Docs: `design-system.md` §5 (ya incluido), `ddd.md`.

## Implementation steps
1. Dominio `Board` + tests de invariantes (INV-01…05).
2. Modelos, migración y repositorio por empresa (INV-06).
3. Casos de uso y puerto `StageCards` + adaptador nulo (AC-05…07).
4. Serializers, vistas y URLs; `required_modules`; errores 400/404/409 (AC-02…08).
5. Sección de defaults + snapshot (AC-01).
6. Pruebas de API, atomicidad, aislamiento y fronteras; `ruff`/`flake8` en lo cambiado.
7. Frontend: modelos, servicio, rutas, menú, i18n.
8. Pantalla `crm-board` y diálogo de archivar (UI-01…05) + specs Karma; `npm run i18n:check`, `npm run lint`, `npm test`.
9. Actualizar `ddd.md` y TASK.

## Database / migrations
Solo creación de tablas; sin datos existentes tocados. Empresas existentes reciben «Ventas» con `copy_company_defaults` o creando el tablero desde la UI.

## Risks
Conflictos de merge con PR 120 (aditivos, documentado); la reasignación real queda sin ejercer en producción hasta PB-CRM-004 (cubierta por pruebas con puerto falso); carrera de reordenamiento (409 + recarga).

## New dependencies
Ninguna.
