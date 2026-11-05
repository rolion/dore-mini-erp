# ADR-cobrar-servicios-anticipos-pagos-parciales-modulo-cobros-y-fuentes: Módulo `receivables` y lectura de las proformas

**Estado:** Propuesto
**Task relacionado:** TASK-cobrar-servicios-anticipos-pagos-parciales
**Fecha:** 2026-11-04

## Contexto
PB-COB-001 pide cobrar líneas **aceptadas** de proformas con anticipos y abonos. Hay dos fuentes con decisiones: `quotations` (genérica) y `dentistry` (con pieza dental, agregado propio). Ventas no sirve como agregado: su `Order` exige `product_id` y cantidades enteras, no imputa pagos por línea ni es idempotente (`sales/infrastructure/django/models.py`). Reutilizamos de Ventas el **contrato de pago** (monto > 0, método = enum `PaymentMethod`, fecha no futura, referencia ≤ 100, monto ≤ saldo), no su agregado. `ddd.md` prohíbe que los módulos se importen infraestructura y obliga a usar fachadas `services`.

## Decisión
1. **Módulo nuevo `modules/receivables`** («Cobros», clave `receivables`) con `domain/ application/ infrastructure/ api/`. Agregado raíz `Obligation` (una por compromiso), con pagos inmutables e imputaciones por línea. Se registra en `MODULE_CATALOG` (`requires=('customers',)`, `optional=('quotations','dentistry')`), no habilitado por defecto, y en `ALLOWED_DEPENDENCIES['receivables'] = {'quotations','dentistry','customers'}` y `CONSUMERS`.
2. **Identidad del compromiso:** `(company_id, source_kind, source_number)` con `source_kind ∈ {quotation, dental}` y `source_number` el número de proforma (`PF-…`/`ODO-…`), **independiente de la versión**. Único en BD → una sola obligación aunque se versione la proforma.
3. **Lectura de la fuente por fachada.** `quotations.services` y `dentistry.services` exponen `get_collectable_commitment(company_id, number)` que devuelve un `CommitmentSnapshot` inmutable (número, versión vigente, estado, cliente y nombre, y por línea: `line_id`, `lineage_id`, descripción, pieza, cantidad, precio, importe y decisión). `lineage_id` = id de la línea en la primera versión (se recorre `origin_line_id`); es la clave estable de imputación entre versiones. Solo es cobrable una proforma **presentada y vigente** y solo sus líneas **aceptadas** (INV: pendientes y rechazadas no son cobrables).
4. **Dirección única de dependencia con marca «cobrada».** Para impedir rectificar líneas con cobro sin ciclo de módulos, `receivables` llama a `quotations.services.lock_commitment_for_collection(company_id, number)` / `dentistry.services…`, que **bloquea la cabecera de la proforma (`select_for_update`)**, devuelve el snapshot fresco y, con `mark_lines_collected(company_id, line_ids)`, marca `collected=True` en esas líneas (columna booleana aditiva en `quotations_proforma_line` y en la tabla de líneas de Odontología). `rectify` de ambos agregados rechaza con 409 («la línea tiene cobros») una línea marcada; `new_version` copia la marca y `_classify` conserva la edición bloqueada. Los módulos fuente no importan `receivables`.
5. **Sin duplicar ventas ni ingresos:** Cobros no crea pedidos de Ventas ni toca inventario. Los ingresos de servicios en Reportes quedan fuera de alcance.
6. **Importe exigible** = Σ importes de líneas aceptadas de la versión vigente; **cobrado** = Σ imputaciones; **saldo** = exigible − cobrado; por línea igual. Todo `Decimal` a 2 decimales (`money()` de la proforma). Las líneas con cobro son inmutables (regla vigente de aceptadas heredadas + marca), por eso el exigible de una línea cobrada nunca baja.
7. **Permisos:** mismo criterio que las fuentes (usuario autenticado con empresa y `required_modules`: `('receivables','quotations')` para fuente genérica, `('receivables','dentistry','customers','services')` para dental). El backend es la autoridad.

## Alternativas consideradas
- **Extender `sales.Order`:** obliga a inventar productos para servicios y mezcla stock/entrega con cobro de servicios; descartado.
- **Que cada fuente guarde sus pagos:** duplica pagos, saldo e idempotencia en dos módulos; descartado.
- **Que `quotations` pregunte a `receivables` si hay cobros al rectificar:** ciclo de dependencia entre módulos; descartado frente a la marca `collected`.
- **Derivar la imputación por `line_id` de la versión:** se rompe al versionar; por eso `lineage_id`.

## Estrategia de rollback / mitigación
Migraciones aditivas (tablas nuevas y una columna booleana con default `False` en dos tablas). Deshabilitar `receivables` retira acceso conservando datos. Rollback de código deja las columnas y tablas intactas; no se aplican migraciones inversas destructivas con datos. Pruebas con dos empresas, fuente ajena, módulo deshabilitado y proforma versionada.

## Consecuencias
Se modifican dos agregados existentes (regla de rectificación y columna `collected`). Duplicación de la fachada en dos fuentes (consistente con el ADR odontológico). Sin reversión de cobros: cualquier corrección exige una tarea posterior. Sin profesional por línea ni honorarios.
