# ADR-catalogo-productos-mvp-contrato-api: Contrato REST de `/api/products/`

**Estado:** Propuesto
**Task relacionado:** TASK-catalogo-productos-mvp
**Fecha:** 2026-10-08

## Contexto
El frontend (DDR `DDR-catalogo-productos-mvp-menu-y-pantallas-producto`) necesita lista con búsqueda por nombre y filtro Activos/Inactivos, alta, edición, detalle y activar/desactivar con confirmación. `ddd.md:920-928` sugiere `GET/POST /api/products`, `GET/PATCH /api/products/{id}` y `POST .../deactivate`. El DRF global ya usa `TokenAuthentication`, `IsAuthenticated` por defecto, solo JSON y `PageNumberPagination` con `PAGE_SIZE=50` (`backend/config/settings/base.py:70-85`); `django-filter` no está instalado y `CLAUDE.md` exige avisar antes de agregar dependencias. El patrón de vistas existente es `APIView` + serializers (`modules/accounts/api/views.py`).

## Decisión
- **Rutas** (montadas en `config/urls.py` como `api/products/` → `modules.catalog.api.urls`; todas requieren token; sin permisos por rol porque no existen roles):

  | Método y ruta | Efecto | Respuesta |
  |---|---|---|
  | `GET /api/products/` | lista paginada | 200 `{count, next, previous, results[]}` |
  | `POST /api/products/` | crea (activo) | 201 producto |
  | `GET /api/products/{id}/` | detalle | 200 producto |
  | `PATCH /api/products/{id}/` | edita `name`, `description`, `sale_price` | 200 producto |
  | `POST /api/products/{id}/activate/` | activa (idempotente) | 200 producto |
  | `POST /api/products/{id}/deactivate/` | desactiva (idempotente) | 200 producto |

  No hay `DELETE` ni `PUT` (405). `active` es de solo lectura en `POST`/`PATCH`; el estado cambia únicamente por `activate`/`deactivate`.
- **Recurso:** `{id (uuid), name, description, sale_price (string decimal, p. ej. "35.00"), active, created_at, updated_at}`. `sale_price` viaja como string para no perder precisión (comportamiento por defecto de DRF); el frontend no hace aritmética monetaria con `float`.
- **Lista:** query params `search` (coincidencia parcial, sin distinguir mayúsculas, por nombre) y `active` (`true`/`false`; ausente = todos); orden fijo por nombre y luego id; implementados a mano en el caso de uso `ListProducts` (sin `django-filter`). Paginación: la de DRF con `page`, más `page_size` opcional (máx. 100) para que la tabla pida 10 filas; sin `page_size` aplica el valor global (50). Búsqueda, filtro y paginación son **del servidor**; la tabla usa paginación externa.
- **Errores:** la validación de forma (serializer: tipos, campos requeridos en `POST`, número decimal) y de reglas (dominio: nombre vacío, precio negativo, más de 2 decimales, fuera de rango) devuelven 400 con el mismo formato `{campo: [mensaje, ...]}` en español; id inexistente o con formato inválido → 404 `{detail}`; sin token → 401 (comportamiento DRF actual). En `PATCH` un `name` enviado vacío es error.
- **Capa API delgada:** las vistas solo parsean/serializan y llaman a los casos de uso; traducen `ProductValidationError` a 400 y "no encontrado" a 404. No hay lógica de negocio en serializers ni vistas.
- **Compatibilidad:** rutas nuevas; no cambia ningún contrato existente (`/api/auth/*`, `/api/health/`).

## Alternativas consideradas
- **`ModelViewSet` + `DefaultRouter`:** menos código, pero ata la API al ORM y salta los casos de uso/dominio del otro ADR; descartado. Se permite un `ViewSet` o `APIView` mientras delegue en `application/`.
- **`django-filter`:** estándar para filtros, pero agrega dependencia para dos parámetros triviales; descartado.
- **Filtrar/paginar en el cliente (traer todo):** más simple al inicio, pero no escala y obligaría a rehacer el contrato; con la paginación de DRF ya configurada el costo en servidor es bajo.
- **Activar/desactivar con `PATCH {active: ...}`:** una ruta menos, pero permite cambiar estado por asignación directa, contrario a "estados por métodos del agregado"; `ddd.md:927` ya prefiere acciones POST. Se agrega `activate` (que el documento no lista) por simetría con REQ-CAT-003.
- **`DELETE`:** contradice conservar historial; excluido.

## Estrategia de rollback / mitigación
Aditivo: rutas nuevas sin consumidores previos. Rollback = revertir el PR (quitar el `include` en `config/urls.py`); el frontend tolera la ausencia mostrando el error de red. No toca autenticación ni autorización (usa la existente tal cual), por lo que no requiere feature flag.

## Consecuencias
- Queda fácil: tabla del frontend con búsqueda/filtro/paginación en servidor; futuros módulos replican el contrato.
- Queda más difícil: el filtro manual hay que mantenerlo (si crecen los filtros se reevaluará `django-filter`).
- Deuda aceptada: sin permisos por rol (el backend solo exige usuario autenticado); sin ordenamiento configurable por el cliente; sin versionado de API.
