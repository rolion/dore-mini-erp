# ADR-perfil-odontologico-pacientes-identidad-y-acceso: Contexto clínico sobre identidad de Clientes

**Estado:** Propuesto
**Task relacionado:** TASK-perfil-odontologico-pacientes
**Fecha:** 2026-11-02

## Contexto
DDD §817/842/848 y ADRs de Clientes, registro/roles y modularidad son la base. Hoy admin accede a datos de su empresa; el usuario confirma que conserva acceso clínico por defecto en v1, sin roles nuevos. Esta decisión no reemplaza todavía el ADR de roles ni concede permisos por registrar un profesional.
## Decisión
1. Nuevo contexto `dentistry`, habilitable por empresa con dependencia obligatoria `customers`. Empresa derivada de sesión; todas las tablas y consultas tienen company_id. No importar accounts desde el contexto.
2. Perfil separado, con UUID propio interno y customer_id por UUID sin FK entre contextos; unicidad de BD `(company_id, customer_id)`. La API expone `id=customer_id`, preservando la identidad del paciente. No copia nombre/teléfono/email. Solo se crea sobre cliente existente de la misma empresa; una carrera de duplicados retorna 409.
3. Antecedentes médicos/odontológicos, alergias, medicación y observaciones son texto opcional limitado. Vacío significa no informado; ausencia requiere declaración explícita. Dominio puro valida y cambia estados con métodos; no confirmaciones clínicas en esta entrega.
4. Nacimiento y responsable son administrativos y pertenecen a Customers: extensión separada `CustomerDemographics`, única por cliente/empresa, con endpoint específico. Evita cambiar el contrato vigente de lista/alta de Customers. Validación de edad/responsable en dominio con fecha actual inyectada; fecha futura rechazada. Nacimiento opcional; menor conocido de 18 requiere nombre/teléfono del responsable. Se leen por fachada administrativa de Customers y se editan explícitamente desde Perfil, sin copia en dentistry.
5. Nueva fachada DTO administrativa en customers (company_id primero), consumida por un adaptador de dentistry. Clínica nunca se devuelve por endpoints de Clientes ni DTO administrativos.
6. Permiso clínico explícito en infraestructura de autorización; admin lo recibe por decisión del usuario. `CompanyClinicalPermission` compone el permiso vigente de empresa/módulos y acceso clínico. Se aplica a lista, detalle, escritura, archivo, capacidades e historial. Frontend consulta capacidades y protege rutas; el servidor sigue siendo autoridad. Ningún usuario/empresa inválido obtiene acceso; no ampliar globalmente CompanyModulePermission.
7. Cada alta/cambio/archivo/reactivación genera evento de auditoría de solo lectura, con autor ID/nombre, hora, acción y cambios anterior/nuevo. Escritura y auditoría en misma transacción, con bloqueo de fila para actualizaciones. Auditoría clínica queda en dentistry; auditoría administrativa en customers. Sin eliminación expuesta, sin datos clínicos en logs. No se registra auditoría de cambios sin modificación efectiva.
8. Archivo conserva perfil, unicidad e historial; no modifica Customer.active. No permite edición clínica hasta reactivar. Las rutas de auditoría están paginadas y filtradas por empresa. Los futuros adjuntos privados se implementarán en PB-ODO-005.
## Alternativas consideradas
- Campos clínicos en Customer: descartado por separación clínica/administrativa y riesgo de fuga por API existente.
- Duplicar identidad en Patient: descartado por requerimiento y divergencia de datos.
- Agregar roles/grupos y administración de usuarios: fuera del alcance autorizado de v1; permiso clínico explícito prepara extensión sin conceder acceso por Personal.
- Demografía en dentistry: descartado porque la tarjeta exige mantener datos administrativos en Clientes.
## Estrategia de rollback / mitigación
Migraciones aditivas, sin editar las aplicadas ni sembrar acceso a nuevos roles. Deshabilitar dentistry detiene acceso sin borrar historia. Revertir aplicación conservando tablas es la mitigación preferida si hay datos clínicos: no ejecutar migración inversa destructiva sin respaldo y decisión operativa. Las APIs existentes de Customers mantienen sus campos. Regresión del permiso global y aislamiento multitenant obligatoria antes de publicar.
## Consecuencias
Nuevo mapa permitido dentistry → customers exclusivamente por fachada; actualizar documentación/tests de límites. Sin Personal, Agenda, dinero, adjuntos ni dependencias de paquetes nuevas.
