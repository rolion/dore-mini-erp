# ADR-registrar-profesionales-y-especialidades-contexto-personal: Contexto Personal independiente

**Estado:** Propuesto
**Task relacionado:** TASK-registrar-profesionales-y-especialidades
**Fecha:** 2026-11-02

## Contexto
Profesional es una persona que atiende, no una cuenta de acceso. La historia actualizada no requiere Agenda ni Sucursales. La arquitectura prohíbe que negocio importe accounts y exige fachadas entre módulos. No hay contrato actual de consulta de usuarios.

## Decisión
Crear `modules/personnel` con dominio Python, casos de uso, repositorios con company_id obligatorio e infraestructura Django/API. Entidades Professional y Specialty, identificadores UUID, asociación de especialidades dentro del contexto, user_id opcional separado de la identidad del profesional. No modificar rol ni autenticación al vincular, desvincular o desactivar.

Guardar autoría como referencia histórica separada del vínculo opcional del profesional, y fechas de creación/actualización/desactivación según la operación; no exponer borrado físico. Las referencias nunca se resuelven sin empresa.

Integrar validación y selector de usuarios mediante un puerto de aplicación implementado en infraestructura compartida de identidad (fuera del módulo de negocio), cableado desde la composición. El adaptador consulta únicamente usuarios de la empresa; ningún import accounts desde personnel. Acceso mantiene propiedad de usuarios y permisos. Cardinalidad confirmada por el usuario: uno a uno; unique sobre user_id no nulo, 400 en user_id al duplicar, preservado al desactivar y liberado al desvincular. No importar modelos de identidad desde el dominio/API de Personal.

Registrar `personnel` como módulo opcional con Acceso como base, sin habilitarlo silenciosamente en empresas existentes. Sus vistas declaran `required_modules=('personnel',)` y reutilizan CompanyModulePermission. Frontend comparte la misma clave con moduleGuard y menú. Actualizar el mapa de límites y la documentación DDD.

API propuesta: `/api/professionals/`, `/api/specialties/`, detalle UUID, PATCH parcial y POST activate/deactivate; selector de usuarios acotado por empresa y autorizado. Lecturas paginadas con search/active y specialty_id para profesionales; relaciones precargadas para evitar N+1. Empresa y autor no proceden del cuerpo. Esquema final en PLAN v2.

Agenda será consumidor futuro de una fachada de Personal; este cambio no añade Agenda, consulta citas ni afirma que ya pueda crearlas. La validación de citas futuras se implementará al integrar ese consumidor, sin consultas a tablas inexistentes.

## Alternativas consideradas
- Extender User: exige cuenta a quien no necesita acceso y mezcla identidad con atención. Descartado.
- Registrar profesionales como clientes/proveedores: reutilización de persistencia con significado de dominio distinto. Descartado.
- Dependencia inmediata de Agenda/Sucursales: contradice el alcance actualizado. Descartado.
- Importar accounts desde Personal: rompe el límite vigente. Usar puerto y composición externa.

## Estrategia de rollback / mitigación
Migraciones aditivas sin editar las existentes. Deshabilitar Personal por empresa permite retirar el acceso conservando datos. Rollback de código no elimina tablas con historial; cualquier reversión de esquema con datos exige copia y decisión operativa explícita. Pruebas de aislamiento con dos empresas, permisos, gate y preservación de autoría. No se migran ni cambian cuentas existentes.

## Consecuencias
Nuevo contexto y gate, sin dependencia de Agenda. Cardinalidad confirmada explícitamente («solo a uno»); el resto del ADR permanece propuesto.
