# ADR-diagnostico-transicion-partida-doble-estrategia-y-contrato: Estrategia y contrato de transición a partida doble

**Estado:** Propuesto
**Task relacionado:** TASK-diagnostico-transicion-partida-doble
**Fecha:** 2026-11-16

## Contexto
`accounting` guarda movimientos de una sola cuenta (32 entradas locales, todas ingresos). El rediseño (CONT-08 en adelante) introduce seis clasificaciones, cuentas con código y asientos de partida doble. La tarjeta CONT-07 exige una transición reproducible, sin pérdida de datos, sin inventar contrapartidas y sin borrar migraciones. El esquema destino aún no existe, así que esta tarea fija el contrato y entrega el diagnóstico; la conversión se ejecuta después.

## Decisión
1. **Dos etapas.** Etapa 1 (esta tarea): diagnóstico de solo lectura + contrato + procedimiento. Etapa 2 (cuando exista el esquema destino): conversión con el mismo contrato. La base de trabajo es la rama `accounting`; no se mergea a `main`.
2. **Solo migraciones incrementales y aditivas.** No se borran, editan ni se hacen `--fake` las migraciones aplicadas (0001–0006 ya están aplicadas en la base local). Las migraciones del esquema destino añadirán columnas/tablas; los datos se transforman con un **comando de gestión explícito**, no dentro de `migrate`, para que `migrate` sobre una base nueva o una copia nunca altere datos de negocio.
3. **Se conservan identidades.** Cada `accounting_account` existente **es** la cuenta de Activo (mismo `id`); las `accounting_entry` no se tocan ni se borran. Cada asiento convertido guarda `entry_id` de origen y los mismos `origin_kind`/`origin_id`/`operation`, de modo que la unicidad `(company, origin_kind, origin_id, operation)` impide duplicados al reejecutar (idempotencia por clave natural).
4. **Mapeos siempre explícitos, nunca por defecto** (patrón de `regularize_ledger`): un archivo JSON por empresa con (a) código de cada cuenta de dinero; (b) por origen/clasificación antigua la cuenta de contrapartida (Ingresos, Gastos o Costos; Pasivo si es anticipo); (c) cuenta de Patrimonio para el saldo de apertura. Lo que no tenga regla queda **pendiente con motivo** y no se convierte. Las clasificaciones INCOME/EXPENSE y `ExpenseCategory` antiguas **no equivalen** a las seis nuevas: solo informan para proponer reglas, no las deciden.
5. **Contrapartida verificable.** Un movimiento solo se convierte si el origen existe (pago/gasto en su módulo, misma empresa y mismo monto), su fecha está dentro de la cobertura y existe regla de contrapartida. Un cobro se convierte como debe = cuenta de dinero, haber = cuenta mapeada; un egreso, al revés; una reversión, como contra-asiento vinculado. Motivos de pendiente: `sin_corte`, `sin_regla_de_contrapartida`, `cuenta_sin_codigo`, `origen_inexistente`, `monto_distinto`, `moneda_distinta`, `empresa_inconsistente`, `anterior_al_corte` (este último no es error: es histórico).
6. **Corte y doble cómputo.** El corte de cada empresa es el ya definido por CONT-06 (`accounting_settings.cutoff_date`). Se convierten solo movimientos con fecha efectiva ≥ corte; los anteriores quedan como histórico en el libro y **no generan asiento** (la apertura ya los resume). Una empresa con entradas y sin corte queda bloqueada por completo hasta que el dueño fije el corte.
7. **Saldos iniciales por asiento balanceado.** Cada `opening_balance > 0` genera un asiento de apertura fechado en el corte: debe = cuenta de Activo, haber = la cuenta de Patrimonio designada. Sin cuenta de Patrimonio designada, o sin corte, queda pendiente. La suma de débitos = la suma de créditos de cada asiento se verifica antes de escribir.
8. **Diagnóstico = previsualización.** El comando `diagnose_ledger_transition` solo lee (sesión PostgreSQL de solo lectura en las pruebas), filtra siempre por `company_id` y produce el inventario, la conciliación contra los orígenes y el estado de cada movimiento. Nunca modifica ni borra.
9. **Respaldo y recuperación.** Antes de cualquier transformación: `pg_dump -Fc` de la base; ensayo obligatorio en una copia restaurada con `pg_restore` en otra base; solo después, la conversión con `--apply`. Recuperación: restaurar el volcado; la conversión es solo-agregar, así que además se puede deshacer eliminando únicamente los asientos marcados como convertidos (por una acción futura de la Etapa 2 con confirmación explícita).
10. **Datos de prueba.** El diagnóstico lista empresas con su volumen, pero no clasifica nada como «de prueba» ni lo borra: cualquier limpieza destructiva requiere decisión explícita del dueño.

## Alternativas consideradas
- **Migración de datos dentro de `migrate`:** rechazada; haría irreproducible el ensayo en copia y mezclaría esquema con negocio.
- **Reiniciar la base o rehacer migraciones (squash/`--fake`):** prohibido por la tarjeta y por `CLAUDE.md`; la base local ya aplicó 0006.
- **Contrapartida por defecto (todo cobro → Ingresos):** rechazada; podría registrar anticipos (pasivo) como ingreso.
- **Convertir también lo anterior al corte:** rechazada; duplicaría el saldo de apertura (decisión 4 del ADR de corte).
- **Crear cuentas nuevas y migrar entradas a ellas:** rechazada; rompería las referencias FK y el historial.

## Estrategia de rollback / mitigación
Etapa 1 no escribe datos de negocio: el único riesgo es de lectura. Para la Etapa 2: respaldo previo, ensayo en copia, `--apply` explícito, conversión idempotente y solo-agregar, y consulta de conciliación posterior (suma de débitos = créditos; suma de la cuenta de dinero convertida = saldo calculado por `account_balances`). Si falla, se restaura el volcado.

## Consecuencias
- El dueño debe decidir (no bloquea la Etapa 1): códigos de las cuentas de dinero; contrapartida de cobros (¿anticipos como Pasivo?) y de gastos/pagos de compras; cuenta de Patrimonio para aperturas; fecha de corte de las 3 empresas sin ella; qué empresas son de prueba.
- Los movimientos sin regla quedan pendientes y no aparecerán en el nuevo libro hasta resolverlos.
- CONT-08 a CONT-13 pueden diseñarse sobre este contrato sin esperar la conversión.
