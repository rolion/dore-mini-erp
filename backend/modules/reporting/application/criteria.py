"""Texto único del criterio de ventas: el dashboard y los reportes muestran exactamente esta cadena."""

LEDGER_CRITERIA = (
    'Libro contable: el flujo es la variación de las cuentas de dinero (Caja, Banco, Billetera) y las transferencias '
    'entre ellas no cuentan; el resultado es Ingresos − Costos − Gastos según la fecha contable de cada asiento. '
    'Comprar inventario, pagar a un proveedor o cobrar una deuda no son gasto ni ingreso. No incluye lo anterior al corte '
    'contable ni es un estado financiero legal.'
)

SALES_CRITERIA = (
    'Ventas: total de los pedidos no cancelados con al menos un producto, según su fecha de pedido. '
    'No equivale a lo cobrado. La ganancia estimada no incluye costo de producción.'
)
