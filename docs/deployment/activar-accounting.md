# Activar accounting en una empresa (runbook)

Guía para habilitar el libro de entradas y completar el histórico. Origen: PB-ACC-005. **Escribir esta guía no despliega ni regulariza nada**: cada paso lo ejecuta una persona administradora, empresa por empresa, primero en un entorno de prueba.

## Qué es y qué no es
- El libro registra **entradas** = dinero recibido por pago de productos (pedidos) y servicios (proformas), con fecha efectiva del pago, cuenta destino y origen (`PRODUCT` / `SERVICE`). Un pago = una entrada, aunque se distribuya en varias líneas.
- Los totales son **entradas registradas**: no son saldo bancario ni utilidad. Las cuentas son destinos de clasificación, no cuentas bancarias.
- No incluye partida doble, contabilidad fiscal, egresos, transferencias, saldos iniciales ni reversiones.
- El reporte ventas − gastos no cambia: no lee el libro.

## Antes de empezar
1. Respaldo de la base de datos (el deploy ya lo hace; en una activación manual, hágalo antes).
2. Confirmar que `main` incluye PB-ACC-001..005 y PB-COB-002 y que las migraciones `accounting` 0001..0003 están aplicadas (`python manage.py showmigrations accounting`).
3. Usar una cuenta **administradora** de la empresa (los miembros reciben 403 en la API de contabilidad).

## Pasos
1. **Habilitar el módulo** `accounting` para la empresa (Ajustes de módulos). Mientras esté deshabilitado, los cobros funcionan como antes y no crean entradas.
2. **Configurar cuentas** (`/pocketbiz/accounting/settings`): crear al menos una cuenta por moneda (BOB) con nombre claro («Caja», «Banco»). La moneda de una cuenta con entradas no se puede cambiar.
3. **Mapear métodos de pago**: asignar a cada método usado (`CASH`, `QR`, `BANK_TRANSFER`, `CARD`, `OTHER`) su cuenta destino. **Sin mapeo, el cobro con ese método se rechaza con 409** y no se guarda nada: configurar antes de habilitar a los cajeros. Cambiar el mapeo después solo afecta a los pagos siguientes; las entradas anteriores conservan su cuenta.
4. **Validar contratos y permisos** (con un token de admin y otro de miembro):
   - `GET /api/accounting/entries/` → 200 para admin, 403 para miembro, 401 sin sesión; `?origin=`, `method`, `account_id`, `date_from`, `date_to`, `page_size`, `page` filtran y los `totals` cubren todas las páginas.
   - `POST /api/accounting/regularization/preview/` y `/apply/` → solo admin; no aceptan `company_id` (la empresa sale de la sesión); `apply` exige `confirm: true`.
   - `POST /api/orders/<id>/payments/` y `/api/receivables/commitments/<kind>/<number>/payments/` con `idempotency_key`: repetir la misma clave devuelve el mismo pago y no crea otra entrada.
5. **Probar un cobro real mínimo** de producto y de servicio (monto pequeño) y confirmar en `/pocketbiz/accounting/entries` que aparecen con su origen. Con Ventas deshabilitado (perfil odontológico) el cobro de proformas sigue funcionando; cobrar no mueve stock ni copia notas al libro.
6. **Previsualizar la regularización** (`/pocketbiz/accounting/regularization` o `python manage.py regularize_ledger --company <uuid> --mapping <archivo.json>` sin `--apply`): indicar periodo y reglas método → cuenta (opcionalmente por rango de fechas si el destino cambió). Revisar el resumen: pagos que se crearían, ya registrados, con entrada en otra cuenta (se informan, no se sobrescriben), pendientes sin mapeo (no se les asigna cuenta por defecto) y conflictos.
7. **Aplicar** solo si la previsualización es la esperada (botón «Aplicar: crear N entradas» con confirmación, o `--apply --executed-by "<nombre>"`). Se crean únicamente los faltantes mapeados; cada entrada conserva fecha, monto, método, referencia y autor originales y guarda aparte fecha y usuario de regularización. No se tocan pagos, imputaciones ni saldos.
8. **Comprobar totales**: repetir la previsualización (debe mostrar 0 por crear) y comparar `totals` del libro con la suma de pagos de la empresa por origen:
   ```sql
   SELECT origin_kind, count(*), sum(amount) FROM accounting_entry WHERE company_id = '<uuid>' GROUP BY 1;
   SELECT sum(p.amount) FROM sales_payment p JOIN sales_order o ON o.id = p.order_id WHERE o.company_id = '<uuid>';
   SELECT sum(amount) FROM receivables_payment WHERE company_id = '<uuid>';
   ```
   (los nombres de tabla deben confirmarse con `\dt` en el entorno antes de ejecutar). Entradas regularizadas: `... WHERE regularized_at IS NOT NULL`.

## Cobertura histórica y pendientes
- Cubre pagos de pedidos (cualquier estado, incluso cancelados, porque conservan sus pagos) y pagos de proformas/obligaciones de Cobros.
- Los pagos con método sin regla quedan **pendientes con motivo**: agregar la regla y repetir; es idempotente.
- Una entrada existente con importe, cuenta o documento distinto se informa como conflicto/diferencia y **no se modifica**.
- El estado «pago anulado» no existe en los orígenes: se informa 0.
- El usuario de regularización es el administrador autenticado (API/pantalla) o el nombre dado en `--executed-by` (comando).
- Los pagos de Ventas históricos no tienen autor ni comprobante: quedan sin esos campos (no se inventan).

## Fuera de alcance (no hay forma de hacerlo hoy)
Reversiones o anulaciones de entradas/pagos, edición manual de entradas, saldos iniciales, transferencias entre cuentas, egresos, partida doble y contabilidad fiscal. Una entrada incorrecta solo se resuelve con una tarea posterior.

## Rollback
Deshabilitar `accounting` devuelve los cobros al comportamiento anterior sin borrar entradas. No hay reversión de entradas regularizadas; por eso la previsualización y el respaldo previo son obligatorios.
