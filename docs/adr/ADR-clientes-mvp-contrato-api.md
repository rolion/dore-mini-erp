# ADR-clientes-mvp-contrato-api: Contrato REST de `/api/customers/` y advertencia de duplicado

**Estado:** Propuesto
**Task relacionado:** TASK-clientes-mvp
**Fecha:** 2026-10-08

## Contexto
El DDR `DDR-clientes-mvp-menu-y-pantallas-cliente` pide: lista con un solo buscador (nombre o teléfono), filtro de estado, alta, edición, perfil, activar/desactivar con confirmación y un diálogo de advertencia cuando el teléfono ya existe, con opción "Crear de todos modos". `ddd.md:930-937` sugiere `GET/POST /api/customers` y `GET/PATCH /api/customers/{id}`. El contrato análogo de productos (`ADR-catalogo-productos-mvp-contrato-api`) ya resolvió paginación de servidor, filtros manuales, errores 400 por campo, `activate`/`deactivate` y vistas `APIView` delgadas; DRF global: Token + `IsAuthenticated`, solo JSON, `PageNumberPagination` (`backend/config/settings/base.py:70-85`).

## Decisión
- **Rutas** (montadas como `api/customers/` → `modules.customers.api.urls`; todas requieren token; sin permisos por rol porque no existen):

  | Método y ruta | Efecto | Respuesta |
  |---|---|---|
  | `GET /api/customers/` | lista paginada | 200 `{count, next, previous, results[]}` |
  | `POST /api/customers/` | crea (activo) | 201 cliente · 409 si hay duplicado sin confirmar |
  | `GET /api/customers/{id}/` | perfil | 200 cliente |
  | `PATCH /api/customers/{id}/` | edita `name`, `phone`, `email`, `notes` | 200 cliente |
  | `POST /api/customers/{id}/activate/` | activa (idempotente) | 200 cliente |
  | `POST /api/customers/{id}/deactivate/` | desactiva (idempotente) | 200 cliente |

  No hay `DELETE` ni `PUT` (405): un cliente nunca se borra (REQ-CUS-005). `active` es de solo lectura en `POST`/`PATCH`.
- **Recurso:** `{id (uuid), name, phone, email, notes, active, created_at, updated_at}`. `phone` es el valor ya normalizado cuando fue posible; los campos opcionales ausentes viajan como `""`.
- **Lista:** query params `search` (nombre o teléfono según el ADR de dominio), `active` (`true`/`false`; ausente = todos, igual que productos; el frontend envía `active=true` por defecto), `page` y `page_size` (máx. 100). Orden fijo por nombre y luego id. Filtros implementados en el caso de uso `ListCustomers`, sin `django-filter`. Esta misma consulta sirve al selector de cliente durante la venta (REQ-CUS-003); Sales no necesita otro endpoint.
- **Duplicado en el alta (REQ-CUS-006):** `POST` acepta el campo booleano opcional `confirm_duplicate` (default `false`). Si `phone` está presente, es no vacío y existe otro cliente (activo o inactivo) con el mismo teléfono normalizado, y no viene `confirm_duplicate: true`, **no se crea** y se responde `409 Conflict` con
  `{"code": "duplicate_phone", "detail": "Ya existe un cliente con este teléfono.", "matches": [{"id", "name", "phone", "active"}]}` (máx. 10 coincidencias). Con `confirm_duplicate: true` se crea normalmente y devuelve 201. El campo `confirm_duplicate` no se persiste ni aparece en el recurso. La detección vive en el caso de uso `CreateCustomer` (que consulta el repositorio), no en el serializer.
- **Alcance de la advertencia:** solo en el **alta**, que es lo que pide REQ-CUS-006. `PATCH` no comprueba duplicados; se registra como límite conocido (ver consecuencias).
- **Errores:** forma/tipos (serializer) y reglas (dominio: nombre vacío o > 150, correo inválido, teléfono > 30, notas > 2000) → 400 `{campo: [mensajes en español]}`, mismo formato que catálogo; id inexistente o con formato inválido → 404 `{detail}`; sin token → 401. Teléfono no normalizable **no es error**.
- **Capa API delgada:** igual que catálogo (`_run` traduce `CustomerValidationError`→400, `CustomerNotFound`→404 y el duplicado→409); el duplicado se modela con una excepción de aplicación (`DuplicateCustomerPhone`) que lleva las coincidencias.
- **Compatibilidad:** rutas nuevas; no cambia contratos existentes.

## Alternativas consideradas
- **Endpoint de verificación previa (`GET /api/customers/check-phone/?phone=`):** permitiría avisar antes de enviar, pero son dos llamadas por alta y la comprobación no es atómica con la creación; descartado, ya que el diálogo al enviar (DDR) basta.
- **Responder 200/201 con una lista `warnings` y crear siempre:** el cliente ya existiría cuando el usuario ve el aviso, incumpliendo "advertencia antes de crear otro cliente". Descartado.
- **400 con error de validación en el campo `phone`:** es bloqueo duro y mezcla un conflicto confirmable con errores de forma; 409 con `code` distingue claramente el caso.
- **Duplicado también en `PATCH`:** protegería mejor los datos, pero REQ-CUS-006 habla de crear y duplicaría el flujo de confirmación en edición; se difiere sin cerrar la puerta (el mismo `confirm_duplicate` serviría).
- **`ModelViewSet`, `django-filter`, `PATCH {active}`, `DELETE`:** descartados por las mismas razones que en el contrato de productos.

## Estrategia de rollback / mitigación
Aditivo: rutas nuevas sin consumidores previos. Rollback = revertir el PR (quitar el `include` en `config/urls.py`); el frontend tolera la ausencia con el aviso de error de red. No cambia autenticación ni autorización; no requiere feature flag.

## Consecuencias
- Queda fácil: el formulario implementa el flujo de confirmación con una sola llamada adicional; el modal de creación rápida desde un pedido reutiliza el mismo `POST` y el mismo 409; el selector de venta reutiliza `GET ?search=&active=true`.
- Queda más difícil: el cliente debe distinguir 409 `duplicate_phone` de otros errores; la mutación idempotente reintentable depende de `confirm_duplicate`.
- Deuda aceptada: la detección no es atómica (carrera entre dos altas simultáneas); `PATCH` puede introducir un duplicado sin aviso; sin permisos por rol; sin versionado de API.
