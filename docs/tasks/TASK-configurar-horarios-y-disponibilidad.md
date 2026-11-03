# TASK-configurar-horarios-y-disponibilidad: PB-AGE-001

**Etapa actual:** PLANNING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-configurar-horarios-y-disponibilidad
**Pull Request:** _sin abrir todavía_
**Fuente:** https://trello.com/c/7MIst1PV/

## Historial de transiciones

| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-03 | (nuevo) → INVESTIGATION | Tarjeta y documentos contrastados con el código | delivery-start |
| 2026-11-03 | INVESTIGATION → DESIGN | Nueva vista semanal y formularios | delivery-start |
| 2026-11-03 | DESIGN → ARCHITECTURE | Agenda consume Personal y persiste reglas propias | delivery-start |
| 2026-11-03 | ARCHITECTURE → PLANNING | Pendiente definir la fuente de zona horaria y turnos nocturnos | delivery-start |

## Investigación

### Requerimiento

[PB-AGE-001](https://trello.com/c/7MIst1PV/) pide configurar turnos semanales con vigencia y pausas, y ausencias por profesional con motivo administrativo. Los turnos contiguos se permiten; los solapados se rechazan. La vista semanal indica la zona horaria y distingue los estados con texto. La ausencia 10:00–11:00 bloquea ese intervalo de un turno 09:00–12:00. Las reservas y el bloqueo por citas futuras afectadas se integran en PB-AGE-002. Un consultorio por empresa, sin sucursales ni recursos físicos. La tarjeta no tiene etiquetas, checklists ni comentarios. La tarjeta y los documentos de [historias](https://docs.google.com/document/d/1pn3nChDn9MRH4wlLCTYWYfHop1sWJfcWVfR0gG6fTHQ) y [especificaciones](https://docs.google.com/document/d/1hH2IGXc-KKod9RAMzfjtnvdg7YvA5CBQKDZABBGS1f8) son insumos.

### Hechos encontrados

- `backend/config/urls.py:6` y `backend/modules/modularity/domain/modules.py:18`: Personal ya está integrado; el catálogo todavía no registra Agenda.
- `backend/modules/personnel/infrastructure/django/models.py:27`: Personal ya posee la entidad persistida de profesional.
- `backend/modules/accounts/models.py:8` y `backend/config/settings/base.py:73`: Company no tiene zona horaria; Django usa un ajuste global que por defecto es UTC.
- `backend/shared/tenancy.py:12` y `backend/config/permissions.py:27`: el backend deriva la empresa de sesión y controla acceso por módulo.
- `docs/design/design-system.md:94`, `:114` y `:135`: patrones para estados, formularios y pantalla de configuración.

### Decisiones confirmadas

- El usuario confirmó que Agenda usa la zona de Bolivia en esta versión y que la configuración por empresa queda para el futuro.
- El usuario confirmó que esta versión no admite turnos nocturnos. Cada turno empieza y termina el mismo día.

### Veredictos

**NEEDS_ARCHITECTURE:** nuevo contexto con persistencia, relación con Personal, control de concurrencia y un contrato temporal que consumirá Citas.
**Diseño requerido: SI:** vista semanal nueva con dos formularios y estados de accesibilidad.

## Diseño

[DDR de la vista semanal](../design/DDR-configurar-horarios-y-disponibilidad-vista-semanal.md).

## Arquitectura

[ADR de límites y tiempo](../adr/ADR-configurar-horarios-y-disponibilidad-limites-y-tiempo.md).

## Plan

**Specification readiness: READY.** [Plan v1](../plans/PLAN-2026-11-03-configurar-horarios-y-disponibilidad.md), modo COMPLETO. Pendiente registrar rama y PR.

## Implementación

_Pendiente._

## Review

_Pendiente._

## Publicación

_Pendiente._
