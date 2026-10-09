# ADR-gastos-reporting-mvp-contrato-api-gastos: Contrato HTTP de Expenses (gastos y categorías)

**Estado:** Propuesto
**Task relacionado:** TASK-gastos-reporting-mvp
**Fecha:** 2026-10-09

## Contexto
El frontend (DDR [menú y pantallas de gastos](../design/DDR-gastos-reporting-mvp-menu-y-pantallas-gastos.md)) necesita: lista de gastos filtrada con el **total de los vigentes del filtro**, formulario, detalle con método de pago, anulación, y gestión de categorías con filtro de estado. Patrón vigente: `APIView` delgadas, `_run` traduce errores de dominio a 400/404/409, paginación `PageNumberPagination` con `page_size` máx. 100, filtros por query params con 400 por parámetro (`customers/api/views.py`, `sales/api/filters.py`, `sales/api/pagination.py`), importes como cadena `"70.00"` (el `money` pipe del frontend recibe `string`), ids UUID como `str` en la URL (id mal formado → 404 `{detail}`). Modelo: [ADR-gastos-reporting-mvp-modelo-dominio-gastos](ADR-gastos-reporting-mvp-modelo-dominio-gastos.md). Autenticación: `IsAuthenticated` global, sin cambios.

## Decisión

**Rutas** (`config/urls.py`: `api/expenses/` y `api/expense-categories/`, ambos a `modules.expenses.api.urls`):

| Método y ruta | Acción |
|---|---|
| `GET /api/expenses/` | Lista paginada y filtrada. |
| `POST /api/expenses/` | Registrar gasto → 201. |
| `GET /api/expenses/{id}/` | Detalle. |
| `PATCH /api/expenses/{id}/` | Editar (cualquier subconjunto de campos editables). |
| `POST /api/expenses/{id}/void/` | Anular → 200 con el gasto. Sin cuerpo. |
| `GET /api/expense-categories/` | Lista de categorías. |
| `POST /api/expense-categories/` | Crear → 201. |
| `GET /api/expense-categories/{id}/` | Detalle. |
| `PATCH /api/expense-categories/{id}/` | Renombrar (`name`). |
| `POST /api/expense-categories/{id}/activate/` y `/deactivate/` | Cambiar estado → 200. |

**No existe `DELETE`** en ninguna ruta: responde 405 (anulación lógica, ver ADR de dominio). Se corrige `ddd.md`.

**Representación de gasto:** `{id, description, amount: "70.00", expense_date: "AAAA-MM-DD", category: {id, name, active}, payment_method: "CASH", supplier_name, notes, status: "ACTIVE"|"VOIDED", voided_at: ISO|null, created_at, updated_at}`. La lista usa la misma forma sin `notes`. `category` embebida evita una segunda llamada y marca "(inactiva)" en la UI.

**Entrada de creación/edición:** `description`, `amount` (cadena o número decimal; el serializer valida forma/tipo con `DecimalField(max_digits=12, decimal_places=2)` como en Sales, las reglas las aplica el dominio), `expense_date`, `category_id`, `payment_method` (opcional, por omisión `CASH`), `supplier_name`, `notes`. En `PATCH` solo se actualizan los campos presentes. `status`, `voided_at` y fechas de auditoría no son editables.

**Filtros de `GET /api/expenses/`:** `date_from`, `date_to` (`AAAA-MM-DD`, inclusive; `date_from > date_to` → 400 en `date_to`), `category_id` (UUID), `status` = `active` (**por omisión**) | `voided` | `all`, `ordering` fijo `-expense_date` (sin parámetro de orden, como Pedidos). `page`/`page_size` (máx. 100). Valores inválidos → 400 `{parametro: [mensaje]}`.

**Total del filtro:** la respuesta paginada incluye `total_amount` (cadena `"0.00"` si no hay filas): **suma de los gastos `ACTIVE` que cumplen los filtros de fecha y categoría, en todas las páginas**, sin importar el filtro `status`. Lo calcula el servidor con una agregación SQL sobre el mismo queryset base; el frontend no suma páginas. Así el número coincide con los reportes.

**Filtros de `GET /api/expense-categories/`:** `active` = `true`|`false` (sin parámetro = todas), `search` por nombre (contiene, sin distinguir mayúsculas). Paginación idéntica; el selector del formulario pide `page_size=100`.

**Errores:**
- Validación (campo): 400 `{campo: [mensajes]}`; categoría inexistente o inactiva: 400 `{category_id: [...]}`; nombre de categoría repetido: 400 `{name: ['Ya existe una categoría con ese nombre.']}`.
- Violación de regla: **409** `{detail, code}` con `code` ∈ `already_voided`, `expense_voided` (editar un gasto anulado).
- No existe: 404 `{detail: 'Gasto no encontrado.'}` / `'Categoría no encontrada.'`.

**Escritura:** `PATCH` y `void` corren en `transaction.atomic()` con `get_for_update` abiertos en la vista (patrón Sales).

## Alternativas consideradas
- **`DELETE /api/expenses/{id}/` como anulación:** semánticamente engañoso (el recurso sigue existiendo y visible con `status=voided`); `POST …/void/` sigue el patrón `deactivate/`/`cancel/` ya usado.
- **`PUT` completo:** el formulario envía todos los campos, pero `PATCH` permite correcciones parciales y es lo previsto en `ddd.md:965`.
- **Total calculado en el frontend sumando la página:** incorrecto con paginación. **Endpoint aparte para el total:** una llamada más y riesgo de desfase con la lista. Se prefiere un campo extra en la respuesta paginada (paginación propia que añade `total_amount`).
- **Categoría solo por id en la respuesta:** obliga a un join en el cliente; embebida cuesta pocos bytes.
- **Sin paginar categorías:** más simple, pero rompe la regla del proyecto de listas paginadas y el número de categorías crece; con `page_size=100` el selector las obtiene de una vez.

## Estrategia de rollback / mitigación
Aditivo: rutas y vistas nuevas sin consumidores previos; no cambia contratos existentes. Rollback = revertir el PR o quitar los `include` de `config/urls.py`. Mitigación de ruptura futura: el frontend tipa la respuesta (`models/`) y las pruebas de API fijan los códigos y claves.

## Consecuencias
- Queda fácil: una lista con total consistente con Reporting; códigos 409 estables para el frontend.
- Queda más difícil: paginación propia con campo extra (una clase `ExpensePagination` que sobreescribe `get_paginated_response`).
- Deuda aceptada: sin filtro por proveedor ni búsqueda por descripción (no pedidos); sin ordenamiento configurable.
