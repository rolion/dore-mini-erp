# ADR-crear-proformas-de-servicios-contexto-congelacion-y-versiones: Contexto Cotizaciones, congelación de precios y versiones

**Estado:** Propuesto
**Task relacionado:** TASK-crear-proformas-de-servicios
**Fecha:** 2026-11-03

## Contexto
PB-COT-001 necesita proformas de servicios con precios trazables. Los servicios (PB-SRV-001) exponen una fachada con snapshot inmutable y su ADR reservó la persistencia de snapshots a este task. `ddd.md` exige dominio puro, repositorios por `company_id` y fachadas como única frontera. Los módulos habilitables se registran en `modularity`.

## Decisión
1. **Nuevo bounded context `modules/quotations`** (`domain/ application/ infrastructure/django/ api/`), clave de módulo `quotations` («Cotizaciones»), `requires=('services', 'customers')`. No habilitado por defecto en empresas existentes. API `/api/quotations/proformas/…`; vistas con `required_modules=('quotations',)` y el permiso por defecto.
2. **Agregado `Proforma`** (raíz) con líneas `ProformaLine`. Estado `draft → presented → superseded` solo por métodos (`present()`, `supersede()`); líneas editables solo en `draft`. El dominio calcula subtotal (`cantidad × precio`, 2 decimales, `ROUND_HALF_UP`) y total; `Decimal` en todo el flujo. Invariantes: cantidad > 0 (≤ 9999.99), precio ≥ 0 (≤ 9 999 999 999.99), presentar exige ≥ 1 línea.
3. **Congelación**: al **incorporar** una línea, la aplicación lee el servicio por `get_service_for_new_use` (activo, de la empresa, módulo habilitado) y copia `service_id`, `description` (nombre) y `unit_price` a la línea; el cliente envía solo `service_id`, `quantity` y, opcionalmente, `unit_price`. Líneas ya existentes (identificadas por id) conservan sus valores aunque el catálogo cambie o el servicio se desactive. Un `unit_price` distinto del vigente solo se acepta si `can_edit_price(user)`; si no, 403. Subtotales y total nunca se aceptan del navegador.
4. **Cliente**: se valida activo al crear/editar borrador por `get_customer_for_sale` y se guarda `customer_name` como snapshot; sin FK entre módulos.
5. **Numeración y versiones**: tabla `ProformaCounter(company_id, last_number)` incrementada con `select_for_update` dentro de la transacción de creación; número `PRO-NNNNNN` único por empresa. `(company_id, number, version)` único. «Nueva versión» copia líneas congeladas de una proforma presentada a un borrador `version+1` (solo si no existe otro borrador del mismo número); al presentar esa versión la anterior pasa a `superseded`, en la misma transacción.
6. **Alcance negativo**: este contexto no importa `sales`, `inventory` ni `agenda`, no crea ventas, cuentas por cobrar, pagos ni movimientos. `accepted_total` se reserva como columna nula no expuesta; `treatment_item_id`/`piece` reservados en línea, sin validación (no existe el módulo de tratamientos).
7. `ALLOWED_DEPENDENCIES['quotations'] = {'service_catalog', 'customers'}` y `CONSUMERS` incluye `quotations`; adaptadores en `infrastructure/adapters.py`. Módulo registrado en `MODULE_CATALOG`.

## Alternativas consideradas
- Ampliar `sales` con «pedido en cotización»: mezcla productos con servicios y arrastra stock; descartado.
- Poner proformas en `service_catalog`: confunde catálogo con documento comercial y acopla; descartado.
- Versionar editando en sitio con historial de eventos: la tarjeta pide versiones consultables con totales propios; copias inmutables son más simples de auditar.
- Consecutivo con `MAX(number)+1`: carrera bajo concurrencia; descartado frente al contador bloqueado.
- Aceptar precio del cliente y validarlo: viola «el backend es la autoridad».

## Estrategia de rollback / mitigación
Migración aditiva (tablas nuevas, sin tocar migraciones aplicadas). Deshabilitar `quotations` retira la API y el menú conservando datos. Rollback de código deja tablas intactas; no aplicar migración inversa destructiva con datos sin respaldo. Pruebas: dos empresas, concurrencia de numeración (PostgreSQL), módulo deshabilitado, precio no autorizado, catálogo cambiado después de guardar.

## Consecuencias
Nueva app Django, clave de módulo, rutas, feature Angular y entradas en el mapa de límites. Estados de aceptación y total aceptado quedan para una historia posterior. Sin dependencias nuevas. Conflictos previsibles con la rama base en `routes.json`, `app.routes.ts`, i18n y `test_boundaries.py`; se resuelven integrando, no reescribiendo.
