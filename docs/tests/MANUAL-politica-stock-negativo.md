# Prueba manual: política de stock negativo (PB-INV-007)

Task: `TASK-politica-stock-negativo` · Plan: `docs/plans/PLAN-2026-10-29-politica-stock-negativo.md`

Hoy ninguna pantalla ni endpoint crea salidas directas de inventario (Ventas aún no descuenta stock y la reversión llega con PB-INV-008). Por eso la parte A se prueba en la UI y la parte B desde el shell de Django, que llama a la misma fachada que usarán Ventas y la reversión.

## Preparación

1. Backend (desde `backend/`, con `.env`): `python manage.py migrate` y `python manage.py runserver`.
2. Frontend (desde `frontend/panel_admin/`): `npm start` (proxy a `127.0.0.1:8000`).
3. Regístrate en `http://localhost:4200/pocketbiz/signup` (crea tu empresa y quedas como admin) e inicia sesión.
4. Habilita el módulo **Inventario** en Configuración → Módulos.
5. Crea en Inventario un almacén «Central» y, en Productos, un producto «Arroz» con **control de stock** y unidad `kg`.
6. En Inventario → Existencias iniciales registra **5 kg** de Arroz en «Central».

## A. Configuración (UI)

| # | Paso | Resultado esperado |
|---|---|---|
| A1 | Abre Inventario → Ajustes (`/pocketbiz/inventory/settings`), pestaña General | Interruptor «Permitir stock negativo» **desactivado**, con la descripción (entregas, ajustes y reversión de recepciones) y «Valor predeterminado: Desactivado» |
| A2 | Activa el interruptor | Aparece «Restablecer»; «Guardar cambios» y «Cancelar cambios» se habilitan |
| A3 | Pulsa «Guardar cambios» | Diálogo «Permitir stock negativo» con la explicación de saldos negativos y botones Cancelar / Permitir |
| A4 | Pulsa **Cancelar** | No se guarda; el interruptor sigue activado y sin guardar (si sales de la pantalla, avisa de cambios sin guardar) |
| A5 | Pulsa «Guardar cambios» → **Permitir** | Aviso «Configuración guardada»; el valor queda activado |
| A6 | Pestaña «Historial de cambios» | Fila con tu usuario, «Permitir stock negativo», anterior **Bloqueado**, nuevo **Permitido** |
| A7 | Vuelve a General, desactiva y guarda | Se guarda **sin** diálogo; el historial suma «Permitido → Bloqueado» |
| A8 | Recarga la página | El valor mostrado coincide con lo guardado |
| A9 | Repite A1–A2 a ~390 px de ancho (modo móvil) y en tema oscuro | Sin desbordes; el diálogo se lee bien |

## B. Salidas y reversión (shell de Django)

Desde `backend/`: `python manage.py shell`. Ajusta el nombre de la empresa si usaste otro.

```python
from decimal import Decimal
from modules.accounts.models import Company
from modules.catalog.infrastructure.django.models import ProductModel
from modules.inventory import services as inv
from modules.inventory.infrastructure.django.models import WarehouseModel
from modules.modularity.infrastructure.django.repositories import DjangoCompanySettingRepository

company = Company.objects.order_by('-created_at').first()   # tu empresa recién creada
cid = company.id
product = ProductModel.objects.get(company_id=cid, name='Arroz')
wh = WarehouseModel.objects.get(company_id=cid, name='Central')
KEY = 'inventory.allow_negative_stock'
policy = DjangoCompanySettingRepository(cid)

def out(qty):
    return inv.record_movement(cid, product_id=product.id, warehouse_id=wh.id, kind='out',
                               quantity=Decimal(qty), user_id=None, user_name='prueba-manual')

def balance():
    return inv.get_balance(cid, product.id, wh.id)

policy.save(KEY, 'false')            # asegúrate de partir bloqueado
print(balance())                     # 5
```

| # | Paso (shell) | Resultado esperado |
|---|---|---|
| B1 | `out('3')` | Se crea la salida; `balance()` → `2` |
| B2 | `out('3')` (bloqueado, solo quedan 2) | Lanza `InsufficientStock`; `balance()` sigue en `2`; no hay movimiento nuevo (compruébalo en Inventario → Movimientos). Revisa `exc.requested == 3`, `exc.available == 2` |
| B3 | `out('2')` (saldo exacto) | Se registra; `balance()` → `0` |
| B4 | `policy.save(KEY, 'true')` y luego `out('4')` | Se registra; `balance()` → `-4`; en Existencias el filtro «Saldo negativo» muestra Arroz |
| B5 | `inv.record_movement(cid, product_id=product.id, warehouse_id=wh.id, kind='in', quantity=Decimal('10'), user_id=None, user_name='prueba-manual')` | Entrada registrada en ambos modos; `balance()` → `6` |
| B6 | Con la política permitida, `policy.save(KEY, 'false')` y luego `out('10')` | Vuelve a rechazar (`InsufficientStock`): la política se lee en cada salida |
| B7 | Reversión: con política bloqueada, revierte la entrada de B5 si ya consumiste parte: `inv.reverse_movement(cid, <id_entrada>, user_id=None, user_name='prueba-manual')` | Si el saldo no alcanza lanza `InsufficientStock`; el movimiento original **no** queda «revertido» |
| B8 | Misma reversión con la política permitida | Se registra el contramovimiento y el saldo puede quedar negativo |

## C. Ajuste de existencias (UI)

| # | Paso | Resultado esperado |
|---|---|---|
| C1 | Inventario → Ajustes de existencias → Nuevo: Arroz, «Central», contado menor que el saldo, motivo, Revisar → Confirmar | Se registra el ajuste (un ajuste nunca deja saldo negativo, con cualquier política) |
| C2 | Con otra pestaña, registra una salida desde el shell entre «Revisar» y «Confirmar» | Aviso «El saldo cambió…»; el formulario conserva producto, almacén, cantidad y motivo |

El aviso de «No hay existencia suficiente» (producto, almacén, solicitada, existencia actual) solo se verá en un ajuste si el servidor devuelve `insufficient_stock`; hoy está cubierto por specs y por pruebas del cuerpo del error. Ventas lo mostrará cuando se conecte.

## D. Concurrencia (opcional)

Con la política **bloqueada** y saldo `5`, abre dos shells y ejecuta `out('4')` casi a la vez (por ejemplo, pegando la línea en ambos y pulsando Enter juntos). Resultado esperado: una sale bien y la otra lanza `InsufficientStock`; el saldo final es `1`, nunca negativo. La prueba automática equivalente es `modules.inventory.tests.test_movements.ConcurrencyTests`.

## Limpieza

`policy.save(KEY, 'false')` para volver al valor por defecto, y desactiva la empresa de prueba desde Django admin (`/admin/`) si ya no la necesitas (las empresas no se borran).
