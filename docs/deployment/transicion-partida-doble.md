# Transición de `accounting` a partida doble (CONT-07, Etapa 1)

Procedimiento, contrato de mapeo y conciliación previos a la conversión. **Esta etapa no convierte ni borra datos**: solo diagnostica. La conversión (Etapa 2) se ejecuta cuando exista el esquema destino (CONT-08/09). Decisiones y motivos: `docs/adr/ADR-diagnostico-transicion-partida-doble-estrategia-y-contrato.md`.

## Reglas
- Base de trabajo: rama `accounting`; no se mergea a `main` en esta tarea.
- Prohibido: borrar o editar migraciones aplicadas, `--fake`, reiniciar la base. Solo migraciones incrementales (`makemigrations`).
- Los datos se transforman con un comando explícito, nunca dentro de `migrate`.
- Toda limpieza destructiva (p. ej. datos de prueba) requiere decisión explícita del dueño.

## Procedimiento
1. **Respaldo** (obligatorio): `pg_dump -Fc -f respaldo.dump <base>`.
2. **Ensayo en copia**: crear una base vacía, `pg_restore -d <copia> respaldo.dump`, apuntar `DATABASE_URL` a la copia y ejecutar `python manage.py migrate` (con el código de `accounting`: debe terminar sin cambios si ya estaba al día) y el diagnóstico.
3. **Diagnóstico** (solo lectura): `python manage.py diagnose_ledger_transition [--company <uuid>] [--mapping <archivo.json>] [--json]`. Sin `--company` recorre todas las empresas, una por una. `--mapping` exige `--company`.
4. **Revisar** pendientes y bloqueos; el dueño decide y completa el mapeo.
5. **Verificación**: repetir el diagnóstico antes y después del `migrate` sobre la copia: los importes deben coincidir.
6. **Recuperación**: restaurar el volcado (`pg_restore --clean`). La conversión de la Etapa 2 solo agrega, así que lo convertido se identifica por su marca y puede retirarse sin tocar el libro original.

Base nueva desde el código de `accounting`: `python manage.py migrate` aplica `accounting` 0001–0006, `expenses` 0003 y `purchases` 0008 sin errores (las migraciones de esta rama son aditivas).

## Contrato de mapeo (por empresa; todo explícito, sin valores por defecto)
```json
{
  "money_accounts": {"<uuid de cuenta de dinero>": "101"},
  "counterparts": {"PRODUCT": "401", "SERVICE": "401", "EXPENSE": "601", "PURCHASE_PAYMENT": "501"},
  "opening_equity": "301"
}
```
- `money_accounts`: cada cuenta de dinero existente **se conserva con su mismo `id`** y pasa a ser una cuenta de Activo con el código indicado (las entradas siguen apuntando a ella; no se crean cuentas nuevas ni se pierden referencias). Códigos únicos.
- `counterparts`: cuenta de la contrapartida por origen (`PRODUCT`, `SERVICE`, `EXPENSE`, `PURCHASE_PAYMENT`). Un código no puede ser a la vez de dinero y de contrapartida. Las clasificaciones INCOME/EXPENSE y las categorías de gastos anteriores **no equivalen** a las seis nuevas: no se traducen solas.
- `opening_equity`: cuenta de Patrimonio contra la que se balancea cada apertura.
- Claves repetidas, cuentas de otra empresa u orígenes desconocidos se rechazan con mensaje y no se aplica nada.

## Estados de cada entrada
| Estado | Significado |
|---|---|
| `convertible_con_regla` | Posterior al corte, con origen verificado y reglas de cuenta y contrapartida |
| `historica` (`anterior_al_corte`) | Anterior al corte: no genera asiento (la apertura ya la resume; sin doble cómputo) |
| `pendiente` | No se convierte. Motivos: `sin_corte`, `cuenta_sin_codigo`, `sin_regla_de_contrapartida`, `origen_inexistente`, `origen_no_verificable`, `monto_distinto`, `moneda_distinta`, `empresa_inconsistente` |

- Una empresa con entradas y sin fecha de corte queda **bloqueada** completa.
- `origen_no_verificable`: Contabilidad no puede leer Gastos ni Compras (la dependencia es en sentido contrario); sus entradas de egreso quedan pendientes hasta que la Etapa 2 defina el puerto de verificación. Hoy no existen entradas de egreso locales.
- Apertura: cada `opening_balance > 0` se convertirá en un asiento balanceado en la fecha de corte (cuenta de Activo contra `opening_equity`); pendiente por `sin_corte`, `cuenta_sin_codigo` o `sin_cuenta_patrimonio`.

## Decisiones del dueño
**Resueltas (2026-11-16):**
- Todos los datos locales son de prueba: no hay nada que conservar; aun así no se borra nada sin pedido explícito.
- Las 3 empresas con entradas y sin fecha de corte (19 entradas) **se dejan bloqueadas**: no se fija corte ni se convierten.
- La contrapartida de cobros y de gastos/compras queda **pendiente**; los movimientos siguen como `pendiente` hasta que se decida.
- Los códigos de las cuentas de dinero no se definen ahora: se fijan en la Etapa 2 con el esquema de CONT-09.

**Abiertas (Etapa 2):** códigos de las cuentas de dinero; contrapartida de cobros (¿Ingresos o Pasivo si es anticipo?) y de gastos/pagos de compras (¿Gastos o Costos?); cuenta de Patrimonio para las aperturas.

## Conciliación de la base local (solo lectura, antes de cualquier transformación)
Base `doredb`, 2026-11-16; `accounting` 0001–0006 aplicadas.

| Concepto | Valor |
|---|---|
| Empresas | 21 (5 con cuentas; 5 con entradas) |
| Cuentas | 9 (3 con tipo, 6 sin tipo); apertura total 1 000,50; ninguna con apertura tiene movimientos |
| Entradas | 32, todas ingreso/registro: 16 PRODUCT = 1 468,50; 16 SERVICE = 2 980,00; total 4 448,50; 19 regularizadas |
| Entradas huérfanas / de otra empresa | 0 / 0 |
| Pagos de ventas | 27 = 2 554,00; **11 sin entrada** (1 085,50) |
| Pagos de cobros | 26 = 3 970,00; **10 sin entrada** (990,00) |
| Pagos de compras / gastos | 12 = 818,50 / 1 = 270,00, sin movimiento ni clasificación |
| Empresas con entradas y sin corte | 3 de 5 (19 entradas) |

**Los 21 pagos sin entrada** (diagnóstico, 2026-11-16): 11 de ventas (1 085,50) y 2 de cobros (165,00) están en empresas con datos de Contabilidad y se informan como `sin_entrada`; los otros 8 de cobros (825,00) son de una empresa **sin ningún dato de Contabilidad** (sin cuentas, entradas ni corte): el recorrido sin `--company` no la incluye, pero `--company <uuid>` sí la diagnostica. Ninguno es anterior al corte.

Resultado del diagnóstico sobre la copia (sin mapeo): 32 entradas, 0 convertibles, 0 históricas, 32 pendientes: 19 `sin_corte` (3 empresas bloqueadas) y 13 `cuenta_sin_codigo`.

## Estado de la verificación
- Pruebas del diagnóstico (7 unitarias y 8 de integración) y regresión de `accounting` (181): en verde. La base de pruebas se crea desde cero aplicando toda la cadena de migraciones sin errores.
- **Ensayo en copia (2026-11-16):** `pg_dump -Fc` de `doredb` (237 602 bytes) → `createdb doredb_copia` → `pg_restore`; el diagnóstico de la copia es idéntico al de la original; `migrate` en la copia: «No migrations to apply»; el diagnóstico tras `migrate` es idéntico (mismos 32 movimientos y 4 448,50). La base original solo se leyó.
