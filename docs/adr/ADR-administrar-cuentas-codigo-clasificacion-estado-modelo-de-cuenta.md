# ADR-administrar-cuentas-codigo-clasificacion-estado-modelo-de-cuenta: Código, clasificación obligatoria y tipo de dinero opcional en la cuenta

**Estado:** Propuesto
**Task relacionado:** TASK-administrar-cuentas-codigo-clasificacion-estado
**Fecha:** 2026-11-16

## Contexto
La cuenta nació como destino de cobros y pagos (CONT-01). El rediseño la convierte en una cuenta del plan contable con código y clasificación (CONT-08/09). El dueño cargará después un plan de 40 cuentas, de las cuales solo Caja y Bancos mueven dinero, y una (Depreciación acumulada) es correctora. El ADR de CONT-08 dejó el código y la obligatoriedad para esta tarea.

## Decisión
1. **Código.** Columna nueva `code` (`varchar(20)`, nulable en base), único por empresa (otra empresa puede usar el mismo código): restricción única parcial sobre `(company_id, lower(code))` donde `code` no es nulo (el `lower` es inocuo con dígitos y permite ampliar el formato). Dominio: recortado, de 1 a 20 **dígitos** (por ahora solo numérico, p. ej. `111001`; los ceros a la izquierda se conservan y `001` y `1` son códigos distintos). El formato lo elige cada empresa; el dueño lo confirmó el 2026-11-16 y se podrá ampliar más adelante. Es obligatorio al crear; las cuentas anteriores quedan con `code` nulo hasta que se editen. El código se puede editar (la identidad es el `id`; las referencias de otros módulos no usan el código).
2. **Clasificación obligatoria al crear.** `account_class` (CONT-08) sigue nulable en base por las cuentas anteriores, pero el alta la exige y debe estar habilitada. Cambiarla requiere que la nueva esté habilitada y que la cuenta **no tenga asientos** (`has_entries_for_account`): si los tiene, 409 `account_has_entries`. Renombrar y cambiar el código no tienen esa restricción.
3. **Tipo de dinero opcional.** `kind` (Caja/Banco/Billetera) deja de ser obligatorio y pasa a significar «cuenta de dinero». Solo se admite cuando la clasificación es Activo; con otra clasificación, `kind` debe estar ausente (400 en `kind`). Cambiar la clasificación de una cuenta con `kind` a una que no sea Activo se rechaza.
4. **Cuenta correctora.** Columna nueva `is_contra` (booleana, falsa por defecto). Es informativa para presentación y reportes (CONT-04 calcula saldos solo con Debe−Haber, sin inferir por clasificación). Se puede fijar al crear y, como la clasificación, no cambia si la cuenta tiene asientos.
5. **Deshabilitar** conserva el contrato actual: activar/desactivar no borra nada; desactivar una cuenta usada por métodos de pago activos responde 409 `account_in_use` con los métodos afectados (decisión del dueño). Las cuentas inactivas siguen en listados y saldos y la fachada las rechaza para usos nuevos (`validate_money_account`). No hay borrado.
6. **API.** Las cuentas (listado, detalle y respuestas de escritura) incluyen `has_entries` (solo lectura: la cuenta ya tiene entradas), calculado con una sola consulta por listado, para que el panel bloquee la clasificación ya asignada y la marca correctora. `POST/PATCH /api/accounting/accounts/` aceptan `code`, `account_class`, `is_contra` y `kind` opcional; `GET` los devuelve. El listado ordena por código (nulos al final) y acepta `?account_class=`. `account_class: null`, `code: null` e `is_contra` ausente en PATCH significan «sin cambio»; en cambio `kind: null` explícito **quita** el tipo de cuenta de dinero (la ausencia de `kind` no cambia nada). Así una cuenta anterior con tipo puede reclasificarse fuera de Activo (REV-01).
7. **Migración `0008`** aditiva: `code`, `is_contra` y la restricción única parcial. No cambia datos.
8. **Fuera de alcance:** cargar el plan de cuentas; restringir el destino de los métodos a cuentas de dinero (CONT-12); asientos con líneas (CONT-02).

## Alternativas consideradas
- **`code` obligatorio en base con relleno:** inventaría códigos para cuentas anteriores; se prefiere nulo.
- **Tabla separada de cuentas contables y cuentas de dinero:** duplica identidades y rompe las referencias de entradas y mapeos; se mantiene una sola `AccountModel`.
- **Inferir «correctora» por nombre o por saldo:** frágil y contrario a CONT-04; se usa un indicador explícito.
- **Código inmutable:** más rígido de lo que pide la tarjeta; el `id` ya garantiza las referencias.

## Estrategia de rollback / mitigación
`migrate accounting 0007` elimina las dos columnas y el índice; son nulables o con valor por defecto, sin datos de otras tablas que dependan de ellas. El contrato más estricto del alta se revierte con el código; las cuentas ya creadas con código conservarían su dato en base hasta el rollback.

## Consecuencias
- El alta de cuentas exige código y clasificación (cambio de contrato aceptado; el cliente es el panel).
- Habrá cuentas anteriores sin código ni clasificación; el diálogo las pide al editar.
- Hasta CONT-12, el selector de métodos de pago puede mostrar cuentas que no son de dinero.
- Cuando CONT-02 cree asientos con líneas, `has_entries_for_account` pasará a mirar las líneas de la cuenta.
