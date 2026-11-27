# ADR-crm-prospectos-oportunidades-modelo-conversion-y-vinculos: Modelo de prospectos/oportunidades, conversión idempotente y vínculos entre contextos

**Estado:** Propuesto
**Task relacionado:** TASK-crm-prospectos-oportunidades
**Fecha:** 2026-11-24

## Contexto
PB-CRM-004 introduce las tarjetas del tablero (oportunidades) y los prospectos. Debe convertir prospectos en clientes sin duplicados, cerrar de forma idempotente, vincular pedidos de Ventas y registrar los cambios de etapa, sin que `crm` conozca modelos de otros módulos ni se salten los límites de empresa.

## Decisión
1. **Mismo contexto `backend/modules/crm/`**, tres tablas nuevas (migración `crm 0002`; la `0001` no se toca): `crm_lead`, `crm_opportunity`, `crm_stage_change`. `company_id` UUID sin FK en prospecto y oportunidad; `board`/`stage` FK internas a `crm`; referencias a otros contextos solo por UUID/entero sin FK (`customer_id`, `order_id`, `owner_id`).
2. **Prospecto** (`Lead`): `name`, `phone` (como se escribió), `normalized_phone` (calculado), `email`, `converted_customer_id` nullable. Sin unicidad por teléfono (varias personas pueden compartir un teléfono; el control de duplicados ocurre contra **clientes**, que es lo que pide la tarjeta).
3. **Oportunidad** (`Opportunity`): `board`, `stage`, `lead_id`/`customer_id` (CheckConstraint: al menos uno), `title`, `owner_id`, `amount` (`Decimal(12,2)` ≥ 0), `currency` (`BOB`), `next_action_at`, `status` (`open|won|lost`), `closed_at`, `order_id`, `lost_reason`. Restricción única condicional sobre `order_id` no nulo (un pedido, una oportunidad). CheckConstraints de coherencia: `won/lost` ⇒ `closed_at` no nulo; `lost` ⇒ `lost_reason` no vacío; `open` ⇒ sin `closed_at` ni `order_id`.
4. **Historial** `StageChange(opportunity, from_stage nullable, to_stage, changed_by nullable, changed_at)`: se escribe al crear (from nulo), al mover y al reasignar por archivo de etapa (changed_by nulo). Solo se agrega, nunca se edita.
5. **Dominio puro** (`crm/domain/opportunity.py`, `lead.py`): agregados `Opportunity` (métodos `move_to`, `close_won`, `close_lost`, `edit`, `link_order`, `attach_customer`) y `Lead` (`convert_to(customer_id)`) con errores de dominio; sin Django. Las transiciones de estado son métodos del agregado.
6. **Puertos nuevos** (`application/ports.py`, adaptadores en `infrastructure/adapters.py`, únicos que importan fachadas): `CustomerGateway` (`normalize_phone`, `find_active_by_phone`, `get_active`, `create`), `OrderGateway` (`get_linkable`/`list_linkable` del cliente: misma empresa, no cancelado), `UserDirectory` (sobre `shared.identity.CompanyUserDirectory`), y el adaptador real **`DjangoStageCards`** del puerto `StageCards` (cuenta y reasigna solo oportunidades abiertas, escribe `StageChange`), que sustituye a `NoCards` en `board_views.stage_cards`. Fachadas nuevas: `customers.services` (`normalize_phone_for_crm`, `find_active_customers_by_phone`, `get_customer_for_crm`, `create_customer_for_crm`) y `sales.services` (`get_order_for_crm`, `list_orders_for_customer_for_crm`), sin exponer modelos.
7. **Conversión idempotente** (`ConvertLead`, `transaction.atomic` + `select_for_update` del prospecto): si ya está convertido devuelve el mismo cliente (200, sin cambios). Si no: usa `customer_id` elegido (debe ser cliente activo de la empresa, 404 si no); si no se envía, busca clientes activos por teléfono normalizado: 1 ⇒ vincula; varios ⇒ 409 `multiple_customer_matches` con candidatos; 0 (o sin teléfono) ⇒ crea el cliente con el nombre/teléfono/email del prospecto (`create_customer_for_crm` confirma el duplicado ya resuelto). Después fija `converted_customer_id` y copia `customer_id` en las oportunidades abiertas del prospecto (conservan `lead_id` como trazabilidad).
8. **Cierre idempotente** (`CloseOpportunity`): `result=won|lost`; repetir el mismo resultado devuelve la oportunidad sin tocar `closed_at`; un resultado distinto sobre una cerrada ⇒ 409 `already_closed`. Perdida exige `lost_reason` (1-500). Ganada admite `order_id` opcional; el vínculo posterior se hace con `PUT /opportunities/{id}/order/` solo estando ganada.
9. **Reglas de vínculo a pedido:** pedido de la empresa (otra empresa ⇒ 404), cliente igual al de la oportunidad (sin cliente ⇒ 409 `customer_required`; distinto ⇒ 409 `order_customer_mismatch`), no cancelado (409 `order_cancelled`), no usado por otra oportunidad (409 `order_already_linked`, respaldado por la restricción única), Ventas habilitado (si no, 409 `sales_disabled`).
10. **Mover:** solo oportunidades abiertas y a etapas **activas del mismo tablero**; otra empresa ⇒ 404; otro tablero/etapa archivada ⇒ 400 en `stage_id`; cerrada ⇒ 409.
11. **Contrato API** nuevo bajo `/api/crm/leads/` y `/api/crm/opportunities/` (ver PLAN), gating `required_modules = ('customers',)`; `card_count` de `/api/crm/boards/` pasa a ser real.
12. **Defaults por empresa:** no cambian (los prospectos y oportunidades son datos operativos, no configuración).

## Alternativas consideradas
- **Un solo modelo «contacto» que sea prospecto o cliente:** mezcla CRM con Clientes y obliga a duplicar o migrar datos. Descartada; el prospecto vive en `crm` y se enlaza al cliente por UUID.
- **Bloquear la conversión ante teléfono duplicado y pedir confirmación en el cliente:** contradice la elección del usuario (vincular al existente). Descartada.
- **Que `crm` importe `customers.application`/`sales.infrastructure` directamente:** viola los límites. Descartada; solo fachadas `services.py` vía adaptadores.
- **Mover/crear oportunidades guardando el historial en la propia fila (JSON):** difícil de consultar y de auditar. Descartada: tabla de cambios de etapa.
- **Reabrir oportunidades cerradas:** no pedido; el usuario eligió cierre definitivo. Descartada.
- **Drag and drop con `cdk`:** se pospone (consistencia con DDR de PB-CRM-003).

## Estrategia de rollback / mitigación
La migración `crm 0002` solo **crea** tablas nuevas y no toca datos existentes; revertir el PR o `migrate crm 0001` las elimina sin afectar a otros módulos (se pierden solo prospectos/oportunidades nuevos). `DjangoStageCards` reemplaza a `NoCards`; volver atrás deja `card_count = 0` y bloquearía ver tarjetas pero no corrompe datos. Conversión y cierre son transaccionales e idempotentes, así que un reintento tras fallo de red es seguro; la restricción única de `order_id` y los CheckConstraints impiden estados inconsistentes aunque falle la validación de aplicación. Un cliente creado por conversión no se borra al revertir (las empresas no pierden clientes); es aceptable porque la conversión es acción explícita de la persona.

## Consecuencias
- `crm` pasa a depender (solo por fachada y desde `adapters.py`) de `customers`, `sales`, `inventory` y `shared.identity`; se actualiza el mapa de `docs/architecture/ddd.md` y `test_boundaries.py`.
- `customers.services` y `sales.services` ganan fachadas de lectura/creación sin cambiar su comportamiento.
- Cerrar una oportunidad no actualiza el pedido ni viceversa (sin sincronización posterior); la vinculación es una referencia.
- Una oportunidad ganada de un prospecto sin convertir no puede enlazar pedido hasta convertir (la UI lo ofrece en el mismo formulario).
