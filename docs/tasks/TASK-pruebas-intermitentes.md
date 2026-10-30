# TASK-pruebas-intermitentes — Pruebas de backend intermitentes

Estado: arreglo aplicado y verificado en SQLite; **pendiente verificar en PostgreSQL** (sin `backend/.env` en este worktree).

## Causa raíz (grupo A: empates de reloj) — fragilidad de las pruebas, no bug de la API
En Windows `datetime.now()` avanza de a ~15,6 ms (`time.get_clock_info('time').resolution = 0.015625`; medido: 13 valores distintos en 200 000 lecturas). Filas creadas seguidas reciben el mismo `auto_now_add`/`auto_now` y los `order_by(..., 'created_at', 'id')` desempatan por UUID aleatorio.
Afecta: `sales` (orden de ítems y pagos: `ItemAndPaymentSyncTests`, `RoundTripTests`), `modularity` `HistoryTests` (`changed_at`, `-id`), `catalog` `updated_at > created_at`.

Evidencia antes (SQLite, Windows, 20 corridas aisladas): ItemAndPaymentSyncTests 17/20 fallan; RoundTripTests 4/20; HistoryTests 8/20; test_patch_updates_fields… 3/20.
Después del arreglo: 0/20 en las cuatro.

## Arreglo aplicado
`shared/test_runner.py` (`StrictClockRunner`, activado con `TEST_RUNNER` en `config/settings/test.py`): `timezone.now()` nunca repite ni retrocede (+1 µs si el reloj real se estanca). Solo afecta pruebas; sin cambio de contrato ni migraciones. Pruebas en `shared/tests/test_test_runner.py`.

## Riesgo real en producción (propuesto, NO aplicado: requiere migración = cambio de contrato)
Ítems/pagos se ordenan por `created_at` + UUID aleatorio: el orden de las líneas de un pedido no está garantizado ni en Linux si dos filas empatan en el mismo µs (raro, pero posible). Arreglo robusto: columna `position` en `OrderItemModel`/`PaymentModel` (y ordenar por ella). Decisión del usuario.

## Grupo B: fallos solo de SQLite (deterministas, no intermitentes)
Con SQLite fallan siempre: `test_orders_by_name_and_filters` (collation binaria: mayúsculas antes que minúsculas), `test_company_name_is_normalized_and_unique_ignoring_case` (`LOWER()` de SQLite no maneja `ñ/É`), y las pruebas de concurrencia (`select_for_update` no existe en SQLite; tabla bloqueada: `ConcurrentSaveTests`, `inventory` Concurrent*, `LockingOutsideTransactionTests`). La regla del proyecto es PostgreSQL para pruebas; no se tocan.
Nota: `test_orders_by_name_and_filters` en PostgreSQL depende de la collation de la base (con `C`/`POSIX` fallaría igual); a confirmar.

## Pendiente (requiere PostgreSQL)
- Suite completa varias veces en PostgreSQL.
- `accounts.test_migrations…test_empty_database_gets_the_default_company_and_nothing_else`: solo se vio en PostgreSQL con la suite completa; no se pudo reproducir en SQLite. Hipótesis: `TransactionTestCase` (flush/estado) deja o borra la empresa por defecto según el orden. Sin evidencia aún.
