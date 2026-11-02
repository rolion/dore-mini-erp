# TASK-administrar-catalogo-servicios: PB-SRV-001

**Etapa actual:** PLANNING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-administrar-catalogo-servicios
**Pull Request:** _sin abrir todavía_
**Fuente:** https://trello.com/c/OmDBYZaq

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-02 | (nuevo) → INVESTIGATION | Tarjeta y fuentes consultadas | delivery-start |
| 2026-11-02 | INVESTIGATION → DESIGN | Pantallas nuevas de catálogo | delivery-start |
| 2026-11-02 | DESIGN → ARCHITECTURE | Nuevo modelo, API y habilitación por empresa | delivery-start |
| 2026-11-02 | ARCHITECTURE → PLANNING | Contrastar alcance de integraciones opcionales | delivery-start |
| 2026-11-02 | PLANNING → PLANNING | Regla de mayúsculas confirmada, aclaración innecesaria sobre Personal retirada; PLAN v2 READY | delivery-start |

## Investigación
### Requerimiento
[PB-SRV-001 · Administrar catálogo de servicios](https://trello.com/c/OmDBYZaq). Insumo funcional, no Specification aprobada por el usuario. Sin etiquetas, checklists ni comentarios al consultar. Administrador mantiene nombre obligatorio, código opcional único por empresa, descripción, precio base BOB no negativo, duración positiva en minutos, especialidad opcional y estado. Lista, alta/edición y detalle bajo Catálogo → Servicios; búsqueda por nombre, estado y especialidad. Crear, editar, activar/desactivar; sin stock ni unidad. Inactivos quedan en historial y no se ofrecen para nuevos usos. Cambios de precio/duración no alteran documentos previos. Ejemplo: 120/30 pasa a 150/45 conservando lo anterior. Rechazar duración cero y referencias ajenas.

Fuentes complementarias leídas: [historias](https://docs.google.com/document/d/1pn3nChDn9MRH4wlLCTYWYfHop1sWJfcWVfR0gG6fTHQ), sección PB-SRV-001 y orden 02/16; [especificaciones](https://docs.google.com/document/d/1hH2IGXc-KKod9RAMzfjtnvdg7YvA5CBQKDZABBGS1f8), secciones 15.1–15.11 y orden de implementación. Confirman módulos independientes, especialidades propiedad de PB-PER-001, consumidor Agenda/Cotizaciones posterior, un consultorio por empresa y ausencia de Sucursales/recursos físicos como prerrequisitos.

### Hechos encontrados
- `backend/modules/catalog/infrastructure/django/models.py:27` — ProductModel tiene precio, usos y control de stock; no representa duración ni especialidad.
- `backend/modules/catalog/infrastructure/django/repositories.py:39` — repositorios reciben empresa y filtran en cada consulta.
- `backend/modules/catalog/domain/product.py:30` — dinero Decimal, dos decimales y máximo 9999999999.99.
- `backend/modules/catalog/services.py:25` — fachada con empresa como primer argumento y DTO inmutable; patrón de integración.
- `backend/modules/sales/domain/order.py:139` — línea de pedido conserva snapshot de producto/precio, sin duración ni servicio.
- `backend/modules/sales/application/commands.py:83` — agregar línea consulta producto activo y vendible. No constituye un contrato de cotización de servicios.
- `backend/config/urls.py:9` — no hay rutas de servicios, especialidades, citas ni proformas.
- `backend/modules/modularity/domain/modules.py:16` — catálogo de habilitación sin Servicios/Personal; módulos base y opcionales ya implementados.
- `backend/config/permissions.py:27` — autorización por empresa activa/admin y required_modules en cada vista.
- `backend/shared/tenancy.py:12` — empresa de sesión, nunca del cuerpo.
- `backend/modules/sales/tests/test_boundaries.py:13` — mapa explícito de dependencias entre contextos y prohibición de importar accounts desde negocio.
- `frontend/panel_admin/src/app/app.routes.ts:36` — Catálogo tiene productos bajo moduleGuard.
- `frontend/panel_admin/src/assets/data/routes.json:26` — menú usa rutas reales bajo /pocketbiz.
- `docs/design/design-system.md:94` — estados comunes; sección 5 define Lista/Formulario/Detalle sobre productos.

Se trajo origin/main: mismo commit c80e360 del checkout inicial. Árbol limpio al comenzar. Búsqueda de specialty/especialidad/proforma/appointment/quotation en backend, features y docs no encontró implementaciones en main. Se inspeccionó además la documentación de la rama ajena `origin/task/TASK-registrar-profesionales-y-especialidades`: propone `modules/personnel`, módulo `personnel` y `/api/specialties/`; no se trata como implementación disponible ni se modifica esa rama.

### Hipótesis / supuestos no confirmados
- Resuelto por el usuario: códigos siempre en mayúsculas, normalizados antes de validar unicidad por empresa.
- Personal sigue ausente: alta sin especialidad permitida por fuente; controles deshabilitados con explicación. Referencias no nulas se rechazan hasta integrar proveedor real. No se requiere otra confirmación por esta dependencia opcional.

### Módulos y dependencias relacionadas
Servicios, Catálogo, Acceso/Empresa y Modularidad. Personal es proveedor opcional de especialidades. Agenda y Cotizaciones son consumidores posteriores, no se implementan como parte del catálogo.
### Implementaciones similares existentes
Productos para pantallas y Decimal; proveedores para maestro sin borrado; fachadas públicas con DTO inmutable para consumo entre módulos.
### Comportamiento actual
Solo existe catálogo de productos. No es posible cumplir el ejemplo completo cotizar/agendar con código de main.
### Restricciones
DDD pragmático, company_id de sesión, Decimal, migraciones nuevas, sin leer/modificar .env ni secretos, sin dependencias nuevas sin aviso. Una rama/PR; no merge automático.
### Riesgos identificados
Confundir producto sin stock con servicio; aceptar UUID ajeno como especialidad sin validarlo; fingir pruebas end-to-end de consumidores inexistentes; cambiar permisos del sistema o ampliar silenciosamente a Personal/Agenda.
### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Modelo persistente/API y módulo habilitable nuevos, más frontera opcional con Personal. Requiere documentar contrato, aislamiento y rollback.
### Diseño requerido
**SI** — Tres pantallas y menú nuevo; seguir Lista/Formulario/Detalle del sistema de diseño.

## Diseño
[DDR-administrar-catalogo-servicios-pantallas](../design/DDR-administrar-catalogo-servicios-pantallas.md), propuesto; especialidad opcional conforme a fuente.
## Arquitectura
[ADR-administrar-catalogo-servicios-contexto](../adr/ADR-administrar-catalogo-servicios-contexto.md), propuesto; sin dependencia obligatoria de Personal.
## Plan
[PLAN-2026-11-02-administrar-catalogo-servicios](../plans/PLAN-2026-11-02-administrar-catalogo-servicios.md) (v2), COMPLETO, **Specification readiness: READY**. Código normalizado a mayúsculas confirmado por usuario. Continuar con PR único y delivery-build.
## Implementación
_Pendiente_
## Review
_Pendiente_
## Publicación
_Pendiente_
