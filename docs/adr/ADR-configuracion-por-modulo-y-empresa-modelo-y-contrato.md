# ADR-configuracion-por-modulo-y-empresa-modelo-y-contrato: Ajustes por módulo y empresa con historial

**Estado:** Propuesto
**Task relacionado:** TASK-configuracion-por-modulo-y-empresa
**Fecha:** 2026-10-27

## Contexto
PB-CFG-001 pide ajustes por módulo y empresa, editables solo por el administrador, con valor inicial documentado, validación, historial (usuario, fecha, valor anterior y nuevo) y sin reescribir documentos históricos. `modularity` ya guarda los módulos habilitados por empresa (`ADR-habilitar-modulos-por-empresa-modelo-y-contrato`). Hoy ningún módulo tiene ajustes; las reglas de Ventas están fijas en código (`backend/modules/sales/domain/order.py:285-292`). Compras e Inventario no existen aún.

## Decisión
1. **Los ajustes viven en `modules/modularity`** (configuración de la empresa; ya es infraestructura no-negocio). Se describe en la documentación como «módulos y configuración por empresa», sin renombrar el app.
2. **Catálogo de ajustes en código** (`domain/settings.py`, sin Django): `SettingDefinition(key, module, label, description, kind, default, choices?, minimum?, maximum?)`. `kind` ∈ `choice` (valores de un enum de negocio, con «sin valor» opcional) y `percent` (Decimal 0–100, 2 decimales). Valores iniciales documentados en el catálogo y en `docs/producto/modulos-implementados.md`. Ajustes de esta historia (todos de Ventas):
   - `sales.default_sales_channel`: `choice` de `SalesChannel` o vacío; inicial vacío.
   - `sales.default_payment_method`: `choice` de `PaymentMethod` o vacío; inicial vacío.
   - `sales.max_discount_percent`: `percent`, inicial `100.00` (igual al comportamiento actual: el descuento no supera el subtotal).
   Compras e Inventario tienen lista vacía. Los valores de `choice` se duplican como constantes en el catálogo y un test los compara con los enums de Sales (el dominio de `modularity` no importa Sales).
3. **Persistencia** (migración nueva `modularity/0002_…`, solo `CreateModel`):
   - `modularity_company_setting(id, company_id UUID indexado, setting_key, value TEXT, updated_at)` con unicidad `(company_id, setting_key)`. **Sin fila = valor inicial del catálogo** (no se siembra). Sin FK a `accounts_company` (convención).
   - `modularity_setting_change(id, company_id indexado, scope, setting_key, setting_label, old_value, new_value, changed_by_id, changed_by_name, changed_at)`. Tabla **append-only** (el repositorio solo inserta y lista). `scope` = clave de módulo o `modules` (activación general). `old_value`/`new_value` son texto ya presentable (p. ej. «WhatsApp», «Habilitado», «100.00 %»); `setting_label` y `changed_by_name` son **snapshots** para que el historial no cambie si se renombra un ajuste o se elimina un usuario; `changed_by_id` es un entero sin FK (no se importa `accounts`; id y nombre llegan desde la vista con `request.user`).
   - La API **nunca guarda ni expone secretos**: el catálogo solo admite `kind` `choice` y `percent`; no hay `kind` secreto y el historial solo registra ajustes del catálogo.
4. **Reglas (dominio puro):** `validate(definition, raw) → valor normalizado` o errores por campo; `choice` exige un valor del catálogo (o vacío si se permite); `percent` exige `Decimal` (nunca `float`) entre 0 y 100 con ≤ 2 decimales. Guardar es **todo o nada**: si un campo es inválido no se guarda ninguno. Solo se registran cambios reales (valor distinto del actual); guardar sin cambios devuelve 200 sin historial.
5. **Contrato API** (permiso por defecto `CompanyAdminPermission`; empresa de `company_id_from(request)`; usuario de `request.user`):
   - `GET /api/settings/<module>/` → `200 {module, settings:[{key,label,description,kind,value,default,choices:[{value,label}],minimum,maximum}]}`. `<module>` = clave de módulo no base del catálogo; desconocida → `404`. Lista vacía para módulos sin ajustes.
   - `PATCH /api/settings/<module>/` con `{ "settings": { "<key>": valor } }` (parcial) → `200` (mismo cuerpo que el GET); `400 {"settings": {"<key>": ["mensaje"]}}` por campo (clave desconocida o valor inválido, sin guardar nada); `404` módulo desconocido; `409 {detail}` si el módulo está deshabilitado para la empresa.
   - `GET /api/settings/<scope>/history/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&setting=<key>&page=<n>` → `200 {count, results:[{id, changed_at, changed_by, setting_key, setting_label, old_value, new_value}], settings:[{key,label}]}` (el último campo alimenta el filtro «Ajuste»); `scope` ∈ módulos no base del catálogo o `modules`; orden `changed_at` descendente; 20 por página; fechas interpretadas en `TIME_ZONE`; formato inválido o `date_from > date_to` → `400`.
   - Compatibilidad: endpoints nuevos; `/api/modules/` no cambia de forma.
6. **Historial de módulos:** `EnableModule` y `DisableModule` reciben el actor y registran, cuando el estado cambia, una fila `scope='modules'`, `setting_key='module.<key>'`, `setting_label=<Nombre del módulo>`, valores «Habilitado»/«Deshabilitado». La operación y su registro van en la misma `transaction.atomic()`.
7. **Ventas consume la configuración por una fachada de solo lectura:** `modules/modularity/services.py::get_sales_settings(company_id) → SalesSettings` (dataclass congelada: `default_sales_channel`, `default_payment_method`, `max_discount_percent: Decimal`). Sales declara el puerto `SalesSettingsReader` (`application/ports.py`) y lo implementa en `infrastructure/adapters.py`. `Order.apply_discount(discount, max_percent=Decimal('100'))` rechaza un descuento mayor que `subtotal × max_percent / 100` con error en el campo `discount`. La regla solo corre al **aplicar un descuento**: no recalcula pedidos con descuentos previos ni reescribe documentos históricos. Los predeterminados de canal y método **no** se aplican en el backend: son sugerencias de la UI (el cliente los lee con `GET /api/settings/sales/`).
8. **Frontera entre módulos:** nuevo permitido `sales → modularity` solo vía `modularity.services` y solo desde `sales/infrastructure/adapters.py`. `test_boundaries.py` se ajusta para ese único caso y conserva la prohibición para los demás módulos de negocio y para `accounts`. `modularity` sigue sin importar módulos de negocio.
9. **Frontend:** `features/settings/` suma `ModuleSettingsComponent`, `SettingsHistoryComponent` (reutilizado en «Módulos») y `SettingsApiService`; guard `canDeactivate` para cambios sin guardar. El formulario de pedido y el registro de pago leen los predeterminados con un `SalesSettingsService` en `features/sales/services/` (si falla, sin predeterminados).

## Alternativas consideradas
- **Tabla clave-valor dentro de Sales (cada módulo guarda sus ajustes):** evita `sales → modularity`, pero duplica validación, historial y API por módulo y rompe el contrato único. Descartada.
- **JSON único por empresa en `Company`:** acopla identidad a configuración y dificulta validar por ajuste/historial. Descartada.
- **Sembrar filas con los valores iniciales en cada empresa:** exige migración o hook por empresa. Descartada: «sin fila = inicial».
- **`django-simple-history`:** dependencia nueva y no controla el formato presentable. Descartada.
- **Aplicar los predeterminados de canal/método en el backend:** cambia el contrato de `POST` de pedidos (canal obligatorio hoy) sin que se pida. Descartada.
- **Permitir editar ajustes de módulos deshabilitados:** mostraría opciones de módulos no usados. Descartada (409).

## Estrategia de rollback / mitigación
Migración solo aditiva (dos tablas): revertir = `migrate modularity 0001` (se pierden ajustes e historial de esa versión, no datos de negocio) o desplegar la versión anterior. Sin fila de ajuste, Sales usa el valor inicial (`max_discount_percent = 100`), idéntico al comportamiento previo; si la lectura falla, el adaptador usa los valores iniciales y registra el error. El frontend sin predeterminados funciona como hoy.

## Consecuencias
- Nuevo acoplamiento acotado `sales → modularity.services` (lectura, DTO inmutable), documentado en `ddd.md` y vigilado por `test_boundaries.py`.
- Cada ajuste nuevo = una entrada en el catálogo (+ su consumo en el módulo dueño); sin migración. Los ajustes P2/P3 se agregan igual.
- Cambiar un valor inicial en código afecta a las empresas que nunca guardaron ese ajuste: es un cambio de comportamiento y debe tratarse como tal.
- El historial crece sin límite por empresa (volumen bajo, cambios manuales); no hay purga en esta historia.
- El historial guarda valores presentables en español: un cambio posterior de etiqueta no los reescribe.
