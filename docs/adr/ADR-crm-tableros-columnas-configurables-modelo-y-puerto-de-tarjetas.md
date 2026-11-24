# ADR-crm-tableros-columnas-configurables-modelo-y-puerto-de-tarjetas: Modelo de tableros/etapas y puerto de tarjetas

**Estado:** Propuesto
**Task relacionado:** TASK-crm-tableros-columnas-configurables
**Fecha:** 2026-11-24

## Contexto
PB-CRM-003 introduce la configuración comercial por empresa: tableros y etapas ordenables y archivables. Las tarjetas (oportunidades) las crea PB-CRM-004, pero ya hoy el archivo de una etapa debe poder reasignarlas «en una transacción». El contexto `crm` se crea de solo lectura en el PR 120 (`TASK-crm-listado-clientes`, base `crm`); esta tarea le añade su primera persistencia.

## Decisión
1. **Mismo contexto `backend/modules/crm/`** (si el PR 120 aún no entró, esta tarea crea el esqueleto: `apps.py`, `api/`, `application/`, `domain/`, `infrastructure/django/`; se resuelve en merge, cambios aditivos). Gating con `required_modules = ('customers',)`, igual que el listado; no se añade clave de módulo.
2. **Modelos** (`crm/infrastructure/django/models.py`, tablas `crm_board`, `crm_stage`): `CRMBoard(id UUID, company_id UUID sin FK, name, is_active, created_at, updated_at)`; `CRMStage(id UUID, board FK, name, position PositiveInteger, is_active, created_at, updated_at)`. `company_id` solo en el tablero; las etapas lo heredan y todo acceso pasa por el repositorio `DjangoBoardRepository(company_id)`, de modo que un id de etapa ajeno nunca resuelve (404).
3. **Unicidad** (restricciones condicionales de BD): nombre de tablero único por empresa sin distinguir mayúsculas entre tableros **activos**; nombre de etapa único por tablero sin distinguir mayúsculas entre etapas **activas**. Archivadas no bloquean nombres. `position`: 1..n contiguo solo entre etapas activas; al archivar, las siguientes se recompactan; la archivada conserva su `position` solo como dato histórico (no se lista).
4. **Dominio puro** (`crm/domain/board.py`): agregado `Board` con métodos `add_stage`, `rename_stage`, `reorder(ids)`, `archive_stage(stage_id, target_stage_id=None, cards_in_stage=0)`, `rename`, `archive`, `reactivate` que validan invariantes y lanzan errores de dominio; sin Django.
5. **Puerto de tarjetas** (`crm/application/ports.py`, `StageCards`): `count(stage_id) -> int`, `reassign(from_stage_id, to_stage_id) -> int`. Adaptador actual `NoCards` (cuenta 0, no mueve nada). PB-CRM-004 aporta el adaptador real (tarjetas viven en su propia tabla dentro de `crm`, así que lo implementa sin cruzar módulos). El caso de uso `ArchiveStage` corre en `transaction.atomic()` con `select_for_update` sobre el tablero: valida, `reassign`, marca la etapa inactiva y recompacta posiciones; si cualquier paso falla, todo se revierte.
6. **Contrato API** bajo `/api/crm/boards/` (ver PLAN): CRUD de tableros, etapas, reordenar (`PUT .../stages/order/` con la lista completa de ids activos) y archivar etapa (`POST .../stages/<id>/archive/` con `target_stage_id` opcional). Errores: 400 validación, 404 id ajeno/inexistente, 409 de regla (`stage_has_cards`, `board_has_cards`, `stage_order_stale`).
7. **Defaults por empresa:** sección `crm` en `crm/infrastructure/defaults.py` (`ORDER` posterior a `modularity`) que crea el tablero **«Ventas» sin etapas** de forma idempotente por nombre; se añade al snapshot con `export_company_defaults`. Empresas existentes: `copy_company_defaults --company …`; además la pantalla ofrece «Crear tablero» si no hay ninguno.

## Alternativas consideradas
- **Nuevo módulo `boards` aparte de `crm`:** duplicaría contexto y menú para un concepto que solo existe para el CRM. Descartada.
- **Reasignar tarjetas desde un servicio de PB-CRM-004 llamado después de archivar:** rompe la atomicidad pedida. Descartada.
- **Borrado físico de etapas:** pierde historia; la tarjeta pide archivo. Descartada.
- **Posición con fracciones/gaps (lexorank):** innecesario para decenas de etapas; enteros contiguos bajo bloqueo de fila bastan.
- **Migración de datos para crear «Ventas» en empresas existentes:** acopla datos de negocio a una migración irreversible; el comando de defaults y el estado vacío de la UI cubren el caso. Descartada.

## Estrategia de rollback / mitigación
Migración `crm 0001` (o `0002` si el PR 120 trajera una) solo **crea** tablas nuevas, sin tocar datos existentes: revertir el PR (o `migrate crm zero`) las elimina sin efectos sobre otros módulos. Si PB-CRM-004 aún no existe no hay tarjetas que perder. El `reassign` y el cambio de estado van en una sola transacción; una falla deja el tablero intacto. Riesgo de carrera mitigado con bloqueo de fila y validación del conjunto completo de ids en `reorder`.

## Consecuencias
- `crm` pasa de lectura a lectura+escritura; el mapa de `docs/architecture/ddd.md` y `test_boundaries.py` se actualizan (sin dependencias nuevas hacia otros módulos).
- PB-CRM-004 debe implementar `StageCards` y consultar etapas activas; hasta entonces el diálogo de reasignación nunca aparece en la práctica (0 tarjetas) pero el contrato y la UI quedan listos.
- Un tablero archivado con nombre repetido de uno activo no se puede reactivar (409 por nombre duplicado).
