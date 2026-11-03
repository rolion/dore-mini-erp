# TASK-configurar-horarios-y-disponibilidad: PB-AGE-001

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-configurar-horarios-y-disponibilidad
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/49
**Fuente:** https://trello.com/c/7MIst1PV/

## Historial de transiciones

| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-03 | (nuevo) → INVESTIGATION | Tarjeta y documentos contrastados con el código | delivery-start |
| 2026-11-03 | INVESTIGATION → DESIGN | Nueva vista semanal y formularios | delivery-start |
| 2026-11-03 | DESIGN → ARCHITECTURE | Agenda consume Personal y persiste reglas propias | delivery-start |
| 2026-11-03 | ARCHITECTURE → PLANNING | Pendiente definir la fuente de zona horaria y turnos nocturnos | delivery-start |

| 2026-11-03 | PLANNING → ENGINEERING | Alcance temporal confirmado y PR #49 abierto | delivery-start |
| 2026-11-03 | ENGINEERING → REVIEW | Implementación publicada y verificaciones pendientes registradas | delivery-build |
| 2026-11-03 | REVIEW → ENGINEERING | FAIL del Quality Gate independiente | delivery-publish |

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

**Specification readiness: READY.** [Plan v1](../plans/PLAN-2026-11-03-configurar-horarios-y-disponibilidad.md), modo COMPLETO. Documentación publicada en el PR #49.

## Implementación

El commit `5f6fba6` implementa la API de Agenda, la migración aditiva y la vista semanal en el PR #49.

- AC-01. La API exige rol administrativo y los módulos Agenda y Personal. Las consultas se acotan a la empresa de sesión.
- AC-02 y AC-03. El dominio valida vigencia, pausas y solapamientos y calcula disponibilidad al descontar pausas y ausencias. El guardado de turnos se serializa por empresa y profesional.
- AC-04. La vista agrupa intervalos por día en hora de Bolivia y reutiliza la tarjeta, el breadcrumb y los controles de formulario del panel. Los formularios se integraron en la pantalla en lugar de usar diálogos como proponía el DDR.

Comprobaciones de ingeniería: tres pruebas de dominio, compilación Angular y `manage.py check`. `makemigrations --check --dry-run` no detectó diferencias entre modelos y migraciones, pero no pudo consultar el historial en PostgreSQL. Pendientes la aplicación de la migración, la integración de permisos y concurrencia en PostgreSQL y el recorrido visual y de teclado en navegador.

## Review

**FAIL** sobre `476397f`. Falló una prueba de límites entre módulos y quedaron sin ejecutar las verificaciones con PostgreSQL. La revisión visual en navegador queda pendiente. El PR #49 sigue en borrador.

- [Falla el límite de arquitectura de Agenda](../reviews/REV-2026-11-03-configurar-horarios-y-disponibilidad-01.md) (High).
- [Faltan pruebas de integración de Agenda](../reviews/REV-2026-11-03-configurar-horarios-y-disponibilidad-02.md) (High).
- [El formulario permite cambios durante el guardado](../reviews/REV-2026-11-03-configurar-horarios-y-disponibilidad-03.md) (Medium).
- [La semana vacía puede quedar sin mensaje](../reviews/REV-2026-11-03-configurar-horarios-y-disponibilidad-04.md) (Medium).

Ingeniería corrigió el adaptador, el estado de semana vacía y la edición durante el guardado. La repetición de dominio y límites pasó 11 pruebas. Pendientes integración PostgreSQL y validación visual.

## Publicación

_Pendiente._
