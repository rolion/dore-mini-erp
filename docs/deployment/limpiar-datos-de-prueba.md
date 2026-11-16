# Limpiar datos operativos de prueba (manual)

Script: `scripts/ops/purge_operational_data.py`. Borra de la base conectada los datos operativos que son de **prueba** (contabilidad, ventas, cobros de servicios, inventario, compras, gastos, proformas, agenda, clientes y catálogo) y conserva usuarios, empresas, migraciones, ajustes de módulos y la configuración contable. La lista exacta está en el encabezado del script. **Es irreversible sin respaldo.** No lo ejecuta ningún pipeline: se corre a mano.

Úsalo solo si todos los datos de la base son de prueba (decisión del dueño, 2026-11-16).

## Antes
1. Respaldo (guárdalo fuera del servidor también):

   ```sh
   docker exec db_v2 pg_dump -U USER -Fc APP_DATABASE > pocketbiz-antes-de-limpiar-$(date +%F).dump
   ```

2. Comprueba que el volcado se lee: `pg_restore -l pocketbiz-antes-de-limpiar-*.dump | grep -c "TABLE DATA"`.
3. Opcional: pon la app en pausa (`docker compose stop frontend`) para que nadie escriba durante el borrado.

## Llevar el script al servidor
El script no está en la imagen del backend: se envía por la entrada estándar. O bien copia el archivo al droplet (`scp scripts/ops/purge_operational_data.py USER@HOST:DEPLOY_PATH/`) y usa los comandos de abajo, o bien ejecútalo desde tu máquina:

```sh
ssh USER@HOST "cd DEPLOY_PATH && docker compose exec -T backend python -" < scripts/ops/purge_operational_data.py
```

## Ensayo (no borra nada)
Desde `DEPLOY_PATH`, con las variables de `docker.md` exportadas:

```sh
docker compose exec -T backend python - < scripts/ops/purge_operational_data.py
```

Muestra la base, las filas por tabla que se borrarían y lo que se conserva, y revierte la transacción. Verifica que el nombre de la base es la de producción y que las cifras son las esperadas.

## Aplicar
```sh
docker compose exec -T -e APPLY=1 -e CONFIRM_DB=APP_DATABASE backend python - < scripts/ops/purge_operational_data.py
```

`CONFIRM_DB` debe coincidir exactamente con el nombre de la base o el script cancela. Todo ocurre en una sola transacción: si algo falla, no se borra nada. Termina con `OK: datos operativos borrados…`.

## Después
- Los mapeos de método de pago quedan **sin cuenta y desactivados**: crea las cuentas y reasígnalos en Contabilidad › Configuración.
- Los cortes y períodos de cobertura se conservan; revísalos.
- Reanuda la app si la pausaste (`docker compose start frontend`).

## Recuperación
Restaurar el volcado (con la app detenida):

```sh
docker exec -i db_v2 pg_restore -U USER -d APP_DATABASE --clean --if-exists < pocketbiz-antes-de-limpiar-YYYY-MM-DD.dump
```

## Límites
- El script no importa modelos y solo toca tablas que existan: sirve aunque producción esté en una versión anterior del esquema.
- Si una tabla ajena a la lista depende de las vaciadas, el `TRUNCATE` falla (no usa `CASCADE`) y no se borra nada: revisa la dependencia antes de insistir.
