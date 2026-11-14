# ADR-crear-cuentas-mapear-metodos-pago-modulo-y-contrato: Módulo `accounting`, catálogo de métodos y precondición de habilitación

**Estado:** Propuesto
**Task relacionado:** TASK-crear-cuentas-mapear-metodos-pago
**Fecha:** 2026-11-13

## Contexto
Hace falta un lugar donde la empresa declare a qué cuenta va el dinero de cada método de pago, antes de tener un libro de entradas. Ventas y Cobros usan los mismos cinco códigos en enums propios (`sales/domain/enums.py:35`, `receivables/domain/obligation.py:19`). `modularity` habilita módulos validando solo dependencias (`use_cases.py:51`) y no conoce `accounting`.

## Decisión
1. **Nuevo bounded context `backend/modules/accounting/`** (`domain/ application/ infrastructure/ api/`, `services.py`), clave de módulo `accounting`, **sin dependencias obligatorias**, opcionales `sales` y `receivables`; no entra en `DEFAULT_ENABLED_KEYS`. API bajo `/api/accounting/` con `required_modules=('accounting',)` salvo la configuración (ver 5).
2. **Correspondencia de métodos explícita:** accounting define su propio catálogo `PAYMENT_METHODS` (`CASH, QR, BANK_TRANSFER, CARD, OTHER`, con etiquetas). Los códigos de Ventas y Cobros son idénticos, así que la correspondencia es la identidad por código; un test compara el catálogo con ambos enums (como ya hace `modularity` con `PAYMENT_METHODS`). Si un código divergiera, el test falla.
3. **Modelo** (`company_id` UUID sin FK entre módulos):
   - `accounting_account`: id, company_id, name (único por empresa sin distinguir mayúsculas y recortado), currency (`BOB`, `USD`), is_active, timestamps. Sin borrado.
   - `accounting_method_mapping`: company_id, method (código), account (FK a `accounting_account`), is_active (defecto true); único `(company_id, method)` → un único destino vigente. Filas ausentes = método activo sin destino.
4. **Reglas:** la moneda de los flujos es `BOB`; solo una cuenta `BOB` y activa puede ser destino de un método; la cuenta debe ser de la misma empresa (404 si es ajena); no se puede desactivar una cuenta con métodos **activos** asignados (409 con la lista; se reasigna, o se desactivan esos métodos); cambiar la moneda de una cuenta con métodos asignados que la volvería incompatible también es 409. Desactivar un método no borra su fila.
5. **Habilitación con precondición:** `EnableModule` recibe un verificador opcional; el puerto neutro `shared/enable_preconditions.py` (patrón de `shared/stock_history.py`) lo resuelve: `accounting` registra su verificador en `AppConfig.ready` y, si hay métodos activos sin cuenta válida, el caso de uso lanza `IncompleteConfiguration` y la API responde 409 `incomplete_configuration` con los métodos faltantes. *(Ajuste de implementación: sustituye al adaptador `modularity → accounting.services` previsto inicialmente; evita romper la regla «modularity no importa módulos de negocio».)* La configuración de cuentas y métodos **no exige** accounting habilitado (hay que poder configurar antes de habilitar); sus endpoints exigen solo admin de empresa. Los endpoints de lectura para otros módulos (`resolve_account`) y futuras entradas sí exigen el módulo habilitado.
6. **Fachada `accounting/services.py`:** `resolve_account(company_id, method)` → DTO inmutable `(account_id, name, currency)` o `None`; `missing_methods(...)`. Es lo que usarán las historias de entradas; el mapeo se resuelve en servidor y la cuenta se **congelará en cada entrada** al cobrar (fuera de esta entrega), de modo que cambiar el mapeo no mueve entradas antiguas.
7. **Sin dependencias nuevas entre módulos:** `accounting` no importa a otros módulos de negocio ni a `modularity`; `modularity` no importa `accounting` (puerto neutro en `shared`). Los métodos activos se validan todos (los flujos de Ventas y Cobros comparten catálogo), por lo que el verificador no recibe los flujos habilitados. Se actualizan `docs/architecture/ddd.md` y el test de fronteras (`accounting: set()`).
8. **Contrato API** (admin de empresa): `GET/POST /api/accounting/accounts/`, `GET/PATCH /api/accounting/accounts/<id>/`, `POST .../activate|deactivate/`, `GET /api/accounting/payment-methods/` (los 5 métodos con su cuenta y estado, completando los no configurados), `PUT /api/accounting/payment-methods/<code>/` (`account_id` y `is_active`).

## Alternativas consideradas
- **Catálogo de métodos en tabla por empresa:** más flexible, pero hoy el conjunto es fijo en ambos flujos; se prefiere catálogo en código + mapeo por empresa (más simple, sin sembrado).
- **Validar la precondición dentro de `modularity` leyendo tablas de accounting:** viola fronteras.
- **Que accounting registre su precondición en un registro global:** más abstracción de la necesaria para un único caso.
- **Multimoneda real:** fuera de alcance; solo se valida compatibilidad con BOB.

## Estrategia de rollback / mitigación
Migración `accounting/0001_initial` solo `CreateModel` (aditiva); revertir = `migrate accounting zero` o simplemente no habilitar el módulo (no está habilitado por defecto y no altera Ventas/Cobros). El comportamiento de empresas existentes no cambia.

## Consecuencias
Un módulo más y una dependencia `modularity → accounting` por fachada. Las historias siguientes consumirán `resolve_account` sin cambiar el contrato. Compras y Gastos quedan sin mapeo hasta su historia de egresos.
