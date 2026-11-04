# TASK-proformas-odontologicas-con-pieza-dental: Proformas dentro de Odontología con pieza dental

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-proformas-odontologicas-con-pieza-dental (basada en `task/TASK-crear-proformas-de-servicios`, PR #52, por indicación del usuario)
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-04 | (nuevo) → INVESTIGATION | Requerimiento en texto libre del usuario | delivery-start |
| 2026-11-04 | INVESTIGATION → DESIGN | Pantallas nuevas dentro de la ficha del paciente | delivery-start |
| 2026-11-04 | DESIGN → ARCHITECTURE | Nuevo agregado en Odontología, migración y dependencia nueva `dentistry → service_catalog` | delivery-start |
| 2026-11-04 | ARCHITECTURE → PLANNING | ADR y DDR escritos; dos decisiones de negocio respondidas por el usuario | delivery-start |
| 2026-11-04 | PLANNING → ENGINEERING | PLAN v1 READY | delivery-start |

## Investigación

### Requerimiento
Texto del usuario (no es una Specification aprobada hasta que se confirme el plan): «creo que el módulo de cotizaciones está bien como un módulo genérico, pero esto puede cambiar un poco para odontología, por ejemplo en la proforma debemos agregar un campo pieza dental, en este campo el doctor agrega el número de diente o código de diente sobre el cual el trabajo, el campo es de tipo texto, **copia proforma dentro de odontología** y agrega el campo pieza dental, es texto y opcional. Dentro de la vista de paciente debería poder verse todas las proformas del paciente y el estado en que se encuentran.»

Aclaraciones obtenidas del usuario en el chat (2026-11-04):
- **Pieza dental por línea** de la proforma (un trabajo por diente), opcional, texto.
- La ficha del paciente muestra **solo las proformas de Odontología** (no mezcla las del módulo genérico Cotizaciones).
- Base: rama del PR #52 (aún sin mergear); la rama y el PR se apilan sobre ella.

### Hechos encontrados
- `backend/modules/quotations/domain/proforma.py` — agregado genérico con líneas congeladas, estados `draft/presented/superseded` y `ProformaLine.piece` reservado, sin exponer.
- `backend/modules/quotations/application/proformas.py` — caso de uso con puertos de servicios/clientes, numeración, versiones, política de precio (`PriceEditNotAllowed`) y cliente activo (INV-06, PLAN v3).
- `backend/modules/dentistry/infrastructure/models.py:5-23` — `PatientModel` único por `(company_id, customer_id)`; el paciente se identifica por `customer_id` (también en la API: `api/urls.py` `patients/<uuid:customer_id>/`).
- `backend/modules/dentistry/api/views.py:40-60` — vistas clínicas con `required_modules = ('dentistry', 'customers')` y `CompanyClinicalPermission` (solo admin en v1).
- `backend/modules/dentistry/infrastructure/adapters.py:1-11` — único punto donde Odontología importa fachadas ajenas (hoy solo `customers`).
- `backend/modules/sales/tests/test_boundaries.py` — `ALLOWED_DEPENDENCIES['dentistry'] = {'customers'}`; `dentistry` ya figura en `CONSUMERS`.
- `backend/modules/service_catalog/services.py:34` — `get_service_for_new_use(company_id, service_id)` devuelve el snapshot (nombre, precio) para nuevos usos.
- `backend/modules/modularity/domain/modules.py:25` — `dentistry` requiere `customers`; `services` es un módulo aparte que la empresa habilita.
- `frontend/panel_admin/src/app/features/dentistry/dentistry.routes.ts` — rutas `patients` y `patients/:id` bajo `clinicalGuard`; `pages/patient-detail.component.html` ya tiene bloques (p. ej. historial en `<details>`).
- `docs/adr/ADR-perfil-odontologico-pacientes-identidad-y-acceso.md` y `docs/architecture/ddd.md:1459` — Odontología extiende la identidad de Clientes sin copiarla y solo puede importar fachadas desde `adapters.py`.
- `frontend/panel_admin/src/app/features/quotations/` — implementación de referencia (lista, formulario con tabla de líneas, detalle, servicio API, i18n `QUOTATIONS.PROFORMAS.*`).

### Hipótesis / supuestos no confirmados
- «Copia» se interpreta como **agregado propio de Odontología** (tablas, API y pantallas propias), no como reutilización del módulo genérico. El módulo `quotations` queda intacto.
- Numeración propia `ODO-NNNNNN` (consecutivo por empresa) para no chocar con `PRO-NNNNNN`.
- Pieza dental: texto libre de hasta 20 caracteres, sin validar contra FDI/universal (admite `18`, `36`, `11-13`).
- Una proforma se crea desde la ficha de un paciente con perfil odontológico **activo**; no hay menú global de proformas de Odontología en esta historia.
- Permisos: igual que el resto de Odontología (admin, `CompanyClinicalPermission`); precio distinto del catálogo solo con la política `can_edit_price` (hoy admin).
- Módulos: las pantallas y la API exigen `dentistry`, `customers` y `services` habilitados; sin `services` la sección no se ofrece.
- Fuera del alcance: aceptar/rechazar, PDF, convertir en tratamiento/cobro, odontograma.

### Módulos y dependencias relacionadas
`dentistry` (nuevo agregado) → `customers` (existente) y `service_catalog` (nueva, solo por fachada desde `adapters.py`). `quotations` no se toca.

### Implementaciones similares existentes
Todo el módulo `quotations` (se replica con cambios) y la sección de historial de la ficha del paciente.

### Comportamiento actual
Odontología no tiene proformas; las del módulo genérico no llevan pieza ni se ven en la ficha del paciente.

### Restricciones
`CLAUDE.md`: `Decimal`, `company_id`, i18n es/en/pt (pipe `translate` / `tr()`), módulos solo por fachada, no editar migraciones aplicadas, sin dependencias nuevas.

### Riesgos identificados
Duplicación de lógica con `quotations` (deuda aceptada por instrucción del usuario); numeración concurrente; coherencia entre paciente archivado y proformas existentes; tamaño del cambio (backend + frontend + i18n).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevo agregado y migración en Odontología, dependencia nueva entre módulos, decisión de duplicar en lugar de compartir.

### Diseño requerido
**SI** — formulario, detalle y sección nueva en la ficha del paciente.

## Diseño
Ver [DDR-proformas-odontologicas-con-pieza-dental-proformas-en-ficha-del-paciente](../design/DDR-proformas-odontologicas-con-pieza-dental-proformas-en-ficha-del-paciente.md).

## Arquitectura
Ver [ADR-proformas-odontologicas-con-pieza-dental-agregado-propio-en-odontologia](../adr/ADR-proformas-odontologicas-con-pieza-dental-agregado-propio-en-odontologia.md).

## Plan
[PLAN-2026-11-04-proformas-odontologicas-con-pieza-dental](../plans/PLAN-2026-11-04-proformas-odontologicas-con-pieza-dental.md) v1 · COMPLETO · Specification readiness: READY.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
