# REV-2026-11-16-configurar-asientos-automaticos-modulo-12: Restos de la versión anterior en comentarios, TASK y orden del Changelog

**Status:** Resolved
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v3)
**Spec reference:** PLAN v2 y v3 (Changelog), INV-02, API-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Tercera pasada, revisión cruzada de código y documentos tras los cambios v2 y v3.

## Expected behavior
Código y documentos vigentes no describen el diseño anterior (clasificación de egreso, tipo Caja/Banco/Billetera como requisito).

## Actual behavior
- `backend/modules/accounting/infrastructure/django/models.py:275`: el comentario de `PostingAccountModel.key` dice «id de la clasificación de gasto»; ahora es el id de la categoría de Gastos.
- `docs/tasks/TASK-configurar-asientos-automaticos-modulo.md` (notas de implementación): la viñeta del dominio dice «tipo Caja/Banco/Billetera para dinero» y la de la API-04 «Activo con tipo Caja/Banco/Billetera»; el riesgo de endurecer el mapeo repite «Activo + Caja/Banco/Billetera». Las líneas añadidas de PLAN v2/v3 las contradicen (el cuerpo sí queda cubierto por el aviso de «Actualización»).
- `docs/adr/...-catalogo-modelo-y-fachada.md`: el cuerpo original conserva `classification_id` en las firmas y `PUT categories/<classification_id>/`; hay dos notas «Actualización 2026-11-17» que rigen, pero el texto sigue siendo engañoso para quien no lea el encabezado.
- PLAN, sección Changelog: el orden es v1, v3, v2; y en el TASK la numeración de decisiones empieza en «00.» y «0.».
- Mensajes de usuario: «Falta la cuenta Caja o Banco…» (`application/posting.py:127` y `:217`) y la etiqueta del rol «Caja o banco del método de pago» siguen hablando de Caja/Banco aunque ya no se exige ese tipo (cualquier cuenta de Activo sirve). No es un error, pero induce a creer que hay un requisito.
- Prueba `test_module_is_ready_only_with_every_active_method_and_category_configured` no verifica categorías (solo ventas y métodos).

## Evidence
`grep` de `classification_id`/`Caja`/`Billetera` en los archivos citados.

## Resolution
Comentario de `PostingAccountModel.key`, mensajes («cuenta de Activo»), etiqueta del rol `MONEY` (es/en/pt), firmas y ruta del ADR, orden del Changelog del PLAN, numeración de desviaciones del TASK y la prueba renombrada.
