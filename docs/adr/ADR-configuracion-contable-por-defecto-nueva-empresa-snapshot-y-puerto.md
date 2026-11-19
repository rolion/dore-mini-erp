# ADR-configuracion-contable-por-defecto-nueva-empresa-snapshot-y-puerto: Snapshot JSON y puerto neutro de defaults por empresa

**Estado:** Aceptado
**Task relacionado:** TASK-configuracion-contable-por-defecto-nueva-empresa
**Fecha:** 2026-11-19

## Contexto
La configuración contable y de módulos de la empresa «demo dore» debe ser el default de toda empresa nueva y copiable a una empresa existente. Esa configuración vive en 6 módulos (`modularity`, `accounting`, `expenses`, `purchases`, `inventory`, más el alta en `accounts`) y se referencia entre sí por UUID propios de cada empresa (categoría de gasto → cuenta; clasificación → ajuste de Compras). Los módulos no importan `accounts` ni infraestructura de otros módulos (`CLAUDE.md`).

## Decisión
1. **Snapshot versionado** `backend/shared/company_defaults/snapshot.json`, con **claves naturales** (código de cuenta, nombre de categoría, nombre+dirección de clasificación, clave de módulo/ajuste). Sin UUID, sin fechas de empresa, sin personas ni movimientos. Lo genera `export_company_defaults --company "demo dore"` (solo lectura) y se revisa en el PR.
2. **Puerto neutro `shared/company_defaults.py`** (mismo patrón que `module_lifecycle`): cada módulo dueño registra desde su `apps.py` un par `export(company_id) -> dict` / `apply(company_id, data, ctx) -> Report` bajo una clave de sección y un `order`. Un orquestador `shared/company_defaults` ejecuta las secciones en orden: `expenses` (categorías) → `inventory` (almacén) → `accounting` (cuentas, mapeos, clasificaciones, cuentas por rol/categoría, corte y período) → `purchases` (ajuste de clasificación) → `modularity` (ajustes y habilitación de módulos). `ctx` es un diccionario compartido de la ejecución que transporta los mapas nombre↔UUID que una sección publica para la siguiente (`classification_ids/names`, `category_ids/names`), de modo que ningún módulo importa a otro. Contabilidad aporta dos secciones (`accounting`, orden 20, y `accounting_posting`, orden 40) porque sus cuentas por categoría dependen de Gastos; orden final: accounting 20 → expenses 30 → accounting_posting 40 → purchases 50 → inventory 60 → modularity 70.
3. **Alta de empresa:** `accounts.registration.register_company_admin` llama a `company_defaults.apply_all(company.id)` dentro de la misma `transaction.atomic()`. Si algo falla, no se crea la empresa. `accounts` solo conoce el puerto de `shared/`, no los módulos.
4. **Copia a empresa existente:** comando `copy_company_defaults --company <nombre|uuid> [--dry-run] [--snapshot ruta]` y `export_company_defaults --company <nombre|uuid> [--output ruta]` (en `modules/accounts/management/commands/`; usan el mismo orquestador). Modo único: **completar lo que falta** (idempotente): crea lo ausente por clave natural, no modifica lo existente, informa creado/existente/omitido por sección. `--dry-run` no escribe.
5. **Fecha de corte y período:** corte = fecha local de aplicación; período fiscal = «<año>» del 1-ene al 31-dic abierto; saldos de apertura 0. Habilitar `accounting` usa la ruta normal de habilitación (cobertura y precondiciones) con los mapeos ya sembrados.
6. **`DEFAULT_ENABLED_KEYS`** no cambia (afecta a empresas ya existentes por siembra perezosa); los 14 módulos se persisten al aplicar los defaults a una empresa. Empresas existentes no cambian salvo que se use el comando.

## Alternativas consideradas
- **Empresa plantilla viva en la BD:** descartada por el usuario (no viaja con el código, frágil ante ediciones).
- **Migración de datos / señal `post_save` de `Company`:** acopla `accounts` con los módulos o esconde el flujo; descartada.
- **Un fixture Django (`dumpdata`):** arrastra UUID y fechas de empresa; no remapea referencias. Descartada.
- **Cambiar `DEFAULT_ENABLED_KEYS` a 14:** alteraría silenciosamente a empresas existentes sin fila. Descartada.

## Estrategia de rollback / mitigación
Sin migraciones: solo código y un JSON. Revertir el PR devuelve el alta al comportamiento actual. La siembra del alta es atómica con la empresa. El comando de copia solo agrega y soporta `--dry-run`; lo creado no pisa datos previos. Fallo de una sección en la copia → transacción por empresa completa revierte.

## Consecuencias
- El puerto es el paquete `shared/company_defaults/` (no un módulo suelto) porque aloja `snapshot.json`; un test de frontera impide que importe `modules.*`.
- Si el snapshot es inválido, `DefaultsError` sube sin capturar y el alta responde 500 (la empresa se revierte): es un error de despliegue, no de la persona usuaria, porque el archivo lo versiona el repo.
- Aplicar el snapshot marca la empresa como inicializada (`CompanySettingsModel`), por lo que la siembra perezosa de `DEFAULT_ENABLED_KEYS` ya no corre para ella. Es seguro mientras el snapshot incluya los módulos por defecto; si se quitan, hay que revisar este acoplamiento.
- Nueva frontera `accounts → shared.company_defaults` y módulos registrando secciones; cubierta por tests de frontera.
- Cada configuración nueva por empresa debe sumar su sección y regenerar el snapshot.
- El snapshot refleja la configuración de «demo dore» en el momento de exportar; editarlo manualmente es válido y se valida al aplicar.
