# ADR-menu-por-tipo-de-empresa-plantilla-inicial: El tipo de empresa es una plantilla inicial de módulos y de menú

**Estado:** Propuesto
**Task relacionado:** TASK-menu-por-tipo-de-empresa
**Fecha:** 2026-11-26

## Contexto
Toda empresa nueva nace con los 14 módulos y un menú de orden fijo (`snapshot.json`, sección `modularity`). Se quiere que, al registrarse, la persona elija el tipo de negocio y obtenga los módulos y el orden de menú que le corresponden, sin impedir que luego habilite más módulos.

## Decisión
1. **Dato.** `Company.company_type`, texto con valores `compraventa`, `servicios`, `odontologia` y `general`. `general` solo lo reciben las empresas existentes (migración `0003`, `default='general'`) y no se acepta en el registro. El tipo no se edita después (ni por API ni por admin de la SPA).
2. **Plantillas de módulos.** Viven en `modules/modularity/domain/company_types.py` (dominio puro: tipo → conjunto de módulos no base). `general` equivale al snapshot actual (los 14).
3. **Puerto de defaults.** `company_defaults.apply_all(company_id, snapshot=None, *, dry_run=False, profile=None)` suma el parámetro opcional `profile`, que se publica en `ctx['profile']`. `apply_modularity` lo lee: con perfil habilita los módulos de la plantilla; sin perfil usa los del snapshot (comportamiento actual de `copy_company_defaults`). El resto de secciones lo ignoran.
4. **Registro.** `register_company_admin(..., company_type)` guarda el tipo y llama `apply_all(company.id, profile=company_type)` dentro de la misma transacción. `accounts` no importa `modularity`: solo pasa la cadena por el puerto. Un test verifica que los tipos aceptados por `accounts` y las plantillas de `modularity` coinciden.
5. **Contrato.** `RegisterSerializer.company_type` es obligatorio y solo admite los tres tipos públicos. `UserSerializer.company` devuelve además `type`.
6. **Menú.** El frontend lee `user.company.type` y reordena los ítems de `routes.json` con una función pura (`arrangeRoutes`) según un diseño por tipo. El filtrado por módulos y rol sigue igual. Los módulos habilitados después que no estén en el diseño del tipo se agregan antes de Ajustes en el orden por defecto.

## Alternativas consideradas
- **Derivar el diseño de los módulos habilitados (sin guardar tipo):** no necesita migración, pero el menú cambiaría al activar un módulo y no hay forma de saber lo que la persona eligió. Descartada porque el requerimiento pide un tipo elegido al registrarse.
- **Tipo editable después:** descartada por decisión del usuario.
- **Un snapshot completo por tipo:** duplica cuentas, mapeos y asientos que son iguales para todos. Descartada: solo varía la lista de módulos.
- **Que `accounts` importe las plantillas de `modularity`:** viola la regla de que los módulos de negocio no se importen con `accounts`. Descartada a favor del parámetro `profile` en el puerto.

## Estrategia de rollback / mitigación
- La migración añade una columna con valor por defecto, sin tocar filas existentes: revertirla es `migrate accounts 0002`.
- Si el registro con tipo falla en producción, `REGISTRATION_ENABLED=False` detiene altas mientras se corrige; las empresas ya creadas no se ven afectadas (siguen con todos los módulos o con la plantilla aplicada).
- El diseño de menú del frontend es aditivo: ante un tipo desconocido o ausente usa el orden actual.

## Consecuencias
- Una empresa nueva ya no recibe los 14 módulos: recibe los de su plantilla y puede habilitar el resto desde Ajustes.
- Cambiar una plantilla afecta solo a empresas futuras.
- Hay dos listas que mantener en sincronía (valores de `CompanyType` en `accounts` y claves de `company_types` en `modularity`), protegidas por un test.
