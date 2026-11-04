# ADR-proformas-odontologicas-con-pieza-dental-agregado-propio-en-odontologia: Agregado propio de proformas en Odontología

**Estado:** Propuesto
**Task relacionado:** TASK-proformas-odontologicas-con-pieza-dental
**Fecha:** 2026-11-04

## Contexto
El módulo genérico `quotations` (ADR de PB-COT-001) cubre cualquier negocio. Odontología necesita una variante con **pieza dental por línea** y verla desde la ficha del paciente. El usuario decidió que el módulo genérico se queda como está y pidió «copiar proforma dentro de odontología». `ddd.md` prohíbe que un módulo importe infraestructura de otro y Odontología solo puede leer fachadas desde `infrastructure/adapters.py`.

## Decisión
1. **Agregado propio `DentalProforma` en `modules/dentistry`** (`domain/ application/ infrastructure/ api/`), copia adaptada de `quotations`: líneas con nombre y precio congelados, `Decimal`, estados `draft → presented → superseded`, versiones, política `can_edit_price`.
2. **Diferencias respecto al genérico:**
   - `DentalProformaLine.dental_piece`: texto opcional, `strip()`, máximo 20 caracteres, una línea (sin saltos). Sin validar contra FDI/universal. Se copia a las nuevas versiones.
   - La proforma pertenece a un **paciente**: se guarda `customer_id` (identidad del paciente en Odontología) y `patient_name` como snapshot. El `customer_id` sale de la URL, nunca del cuerpo. Se exige perfil odontológico **activo** al crear, guardar, presentar y crear versión (paciente inexistente → 404; archivado → 409).
   - Numeración propia `ODO-NNNNNN` por empresa, con su contador bloqueado (`select_for_update`).
3. **Tablas nuevas, sin FK a otros módulos:** `dentistry_proforma`, `dentistry_proforma_line`, `dentistry_proforma_counter`; únicos `(company_id, number, version)`; índices `(company_id, customer_id, status)`; `CheckConstraint` de cantidad > 0 y precio ≥ 0. Migración `0002` aditiva de `dentistry`.
4. **API** bajo `/api/dentistry/`: `patients/<customer_id>/proformas/` (GET lista paginada con filtro `status`, POST crear), `proformas/<id>/` (GET, PUT sobre borrador), `proformas/<id>/present/` y `proformas/<id>/new-version/`. Vistas con `required_modules = ('dentistry', 'customers', 'services')` y `CompanyClinicalPermission`.
5. **Dependencia nueva `dentistry → service_catalog`** únicamente por `modules.service_catalog.services.get_service_for_new_use` desde `infrastructure/adapters.py`; se registra en `ALLOWED_DEPENDENCIES['dentistry'] = {'customers', 'service_catalog'}`. No cambia `requires` de `dentistry` en `modularity` (no se rompe ninguna empresa existente): sin `services` habilitado, los endpoints de proformas responden `module_disabled` y la UI no ofrece la sección.
6. **El módulo `quotations` no se modifica**; sus columnas reservadas `treatment_item_id`/`piece` siguen sin uso.
7. La ficha del paciente lista solo proformas de Odontología (decisión del usuario).

## Alternativas consideradas
- **Reutilizar `quotations` por fachada y extenderlo con pieza:** menos código, pero mezcla lo dental en el módulo genérico o crea una dependencia `dentistry → quotations` y datos compartidos; descartado por la instrucción explícita del usuario de copiar.
- **Extraer el dominio común a `shared/` y especializar:** elimina la duplicación, pero es una abstracción nueva que `CLAUDE.md` desaconseja sin necesidad real y obliga a modificar `quotations`; queda como mejora futura si aparece una tercera variante.
- **Pieza dental en la cabecera:** descartado por el usuario (va por línea).

## Estrategia de rollback / mitigación
Migración aditiva (tablas nuevas). Deshabilitar `services` o `dentistry` retira acceso conservando los datos. Rollback de código deja las tablas intactas; no aplicar migración inversa destructiva con datos sin respaldo. Pruebas con dos empresas, paciente ajeno, archivado, módulo deshabilitado, numeración concurrente.

## Consecuencias
Duplicación consciente de unas ~500 líneas respecto de `quotations` (cambios de reglas de proforma deberán hacerse en ambos hasta una posible extracción). Más superficie de i18n y pruebas. Sin dependencias de paquetes nuevas.
