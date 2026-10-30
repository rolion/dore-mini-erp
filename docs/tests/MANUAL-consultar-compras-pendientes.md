# Prueba manual: consultar compras y sus pendientes (PB-COM-006)

Task: `TASK-consultar-compras-pendientes` · Plan: `docs/plans/PLAN-2026-10-30-consultar-compras-pendientes.md` · PR: https://github.com/rolion/dore-mini-erp/pull/39

## 1. Preparar el entorno (desde el worktree)

Backend (`backend/`, con su `.env` y PostgreSQL):

```bash
python manage.py migrate
python manage.py runserver
```

Frontend (`frontend/panel_admin/`; el backend debe estar en `127.0.0.1:8000`):

```bash
npm start
```

Abre http://localhost:4200/pocketbiz/signup, crea un usuario (queda como admin de su empresa) e inicia sesión. Compras está deshabilitado por defecto: habilítalo en **Configuración → Módulos** (o con el paso de datos de abajo).

## 2. Datos de prueba

Sustituye `TU_USUARIO` y ejecútalo con `python manage.py shell` en `backend/`. Crea 2 proveedores y 7 compras, con pagos, y habilita Compras. No toca otros datos.

```python
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from modules.modularity.domain.modules import DEFAULT_ENABLED_KEYS
from modules.modularity.infrastructure.django.models import CompanyModuleModel, CompanySettingsModel
from modules.purchases.infrastructure.django.models import PaymentModel, PurchaseModel, SupplierModel

company = get_user_model().objects.get(username='TU_USUARIO').company
CompanySettingsModel.objects.get_or_create(company_id=company.id)
for key in (*DEFAULT_ENABLED_KEYS, 'purchases'):
    CompanyModuleModel.objects.get_or_create(company_id=company.id, module_key=key)
sur = SupplierModel.objects.create(company_id=company.id, name='Distribuidora Sur')
norte = SupplierModel.objects.create(company_id=company.id, name='Comercial Norte')

def compra(prov, dia, status='draft', rec='not_received', pago='unpaid', total='50.00', ref='', pagado=None):
    p = PurchaseModel.objects.create(
        company_id=company.id, supplier_id=prov.id, purchase_date=date(2026, 10, dia), status=status,
        reception_status=rec, payment_status=pago, total=Decimal(total), external_reference=ref)
    if pagado:
        PaymentModel.objects.create(company_id=company.id, purchase_id=p.id, amount=Decimal(pagado),
                                    payment_method='CASH', payment_date=date(2026, 10, dia),
                                    status='confirmed', user_name='prueba')

compra(sur, 1)                                                              # A borrador
compra(sur, 2, 'cancelled')                                                 # B cancelada
compra(sur, 5, 'confirmed', ref='FAC-0042')                                 # C confirmada, sin recibir, sin pagar
compra(sur, 8, 'confirmed', pago='partial', pagado='20.00', ref='FAC-0043') # D sin recibir, pago parcial (saldo 30)
compra(norte, 10, 'confirmed', 'received', 'unpaid', ref='REM-7')           # E recibida, sin pagar (saldo 50)
compra(norte, 12, 'confirmed', 'partial', 'paid', pagado='50.00')           # F recibida parcial, pagada (saldo 0)
compra(norte, 15, 'confirmed', 'received', 'partial', total='120.00', pagado='40.00')  # G recibida, pago parcial (saldo 80)
```

Si prefieres no usar el `shell`, crea las compras desde la pantalla (Nueva compra → Confirmar → Registrar recepción/pago); los pasos de abajo valen igual.

## 3. Casos

Abre **Compras → Compras** (`/pocketbiz/purchases`). Marca cada caso OK / FALLA.

| # | Qué hacer | Resultado esperado | AC |
|---|---|---|---|
| 1 | Entrar a la lista sin filtros | Columnas: Referencia (COM-XXXXXXXX, con la referencia externa pequeña debajo), Fecha, Proveedor, Total, Recepción, Estado, Pago, Saldo, Acciones. Las 7 compras. Sin texto recortado | AC-07 |
| 2 | Mirar A (borrador) y B (cancelada) | «—» en Recepción, Pago y Saldo. Solo el borrador tiene lápiz de editar | AC-01, AC-07 |
| 3 | Mirar E y F | E: «Recibida» + «Sin pagar», saldo Bs 50.00. F: «Recibida parcialmente» + «Pagada», saldo Bs 0.00. Los estados se ven separados | AC-06 |
| 4 | Mirar D y G | D: saldo Bs 30.00. G: total 120, saldo Bs 80.00 | AC-06 |
| 5 | Recepción = **Recibida** y Pago = **Pago pendiente** | Solo E y G. La URL cambia a `?receptionStatus=received&paymentStatus=pending` | AC-03, AC-08 |
| 6 | Pago = **Pagada** | Solo F | AC-02 |
| 7 | Pago = **Sin pagar** | C y E (los borradores no aparecen) | AC-02 |
| 8 | Estado = **Borrador** | Solo A. Estado = **Cancelada** → solo B | AC-02 |
| 9 | Proveedor = Comercial Norte | E, F y G. El selector busca escribiendo | AC-02 |
| 10 | Desde 10/10/2026 y Hasta 12/10/2026 | E y F (extremos incluidos) | AC-02 |
| 11 | Desde 15/10/2026 y Hasta 01/10/2026 | Mensaje «La fecha «Hasta» no puede ser anterior a «Desde»» y la lista no se recarga | AC-11 |
| 12 | Buscar `fac-004` | C y D (sin distinguir mayúsculas) | AC-04 |
| 13 | Buscar `COM-` + los 4 primeros caracteres de la referencia de una compra | Aparece esa compra | AC-04 |
| 14 | Buscar `zzzz` | Estado vacío con filtros: «No hay compras que coincidan…», el filtro aplicado como badge, «Limpiar filtros» y «Nueva compra» | AC-09 |
| 15 | Con un filtro activo, pulsar «Limpiar filtros» (también el del vacío) | Vuelve la lista completa y la URL queda sin parámetros. El botón está deshabilitado sin filtros | AC-08 |
| 16 | Con filtros puestos, entrar al detalle y volver con «Atrás» del navegador | Los filtros se restauran desde la URL | AC-08 |
| 17 | Recargar la página (F5) con filtros en la URL | Mismos filtros y mismos resultados | AC-08 |
| 18 | Vaciar la empresa de compras (cuenta nueva) | Mensaje «Aún no hay compras. Crea la primera con «Nueva compra».» sin badges de filtros | AC-09 |
| 19 | Botón «+» de la cabecera | Lleva a `/pocketbiz/purchases/new` | AC-07 |
| 20 | Abrir el detalle de D (ojo o referencia), pestaña **Resumen** | Muestra total, total pagado, saldo y los tres estados por separado; Recepciones y Pagos siguen funcionando | AC-10 |
| 21 | Apagar el backend y recargar | Aviso rojo de error con «Reintentar»; al encender y pulsar, carga | AC-11 |

## 4. Revisión visual

- **Escritorio (≈1440 px):** sin texto recortado; «Pago parcial» y «Recibida parcialmente» pueden ocupar dos líneas dentro de su badge (verifica que sigan legibles); los botones de Acciones de un borrador caben en una fila.
- **Móvil (≈390 px):** la página no tiene scroll horizontal (la tabla se desplaza dentro de su tarjeta); los filtros se apilan.
- **Tema oscuro:** textos y badges legibles; las cabeceras «Total» y «Saldo» alineadas con sus valores (esto último no pude confirmarlo yo).
- Cada estado tiene texto además del color.

## 5. Pendientes que conviene decidir al probar

- **H-01:** borradores y canceladas muestran «—» y desaparecen al filtrar por recepción o pago. ¿Es lo que quieres?
- **H-02:** «Pago pendiente» = sin pagar + pago parcial.
- Los colores de los badges de recepción y pago no coinciden con los del DDR (usan los de PB-COM-005).

## 6. Limpieza

Los datos del paso 2 se borran con `SupplierModel.objects.filter(name__in=['Distribuidora Sur', 'Comercial Norte']).delete()` y `PurchaseModel.objects.filter(external_reference__in=['FAC-0042','FAC-0043','REM-7']).delete()` (más las compras sin referencia, desde Django admin si las quieres quitar).
