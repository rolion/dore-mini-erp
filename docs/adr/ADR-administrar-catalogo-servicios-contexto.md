# ADR-administrar-catalogo-servicios-contexto

**Estado:** Propuesto
**Task relacionado:** TASK-administrar-catalogo-servicios
**Fecha:** 2026-11-02

## Contexto
Las especificaciones sección 15 definen Servicios como capacidad modular independiente y el refinamiento lo sitúa bajo Catálogo en el menú. Productos actuales tienen semántica de inventario y no duración. Personal no está en main; se respeta propiedad de especialidades en PB-PER-001. ddd.md exige dominio puro y fachadas como única frontera entre módulos.
## Decisión
Proponer `modules/service_catalog` (evita confundir el paquete con la fachada services.py), clave de habilitación `services`, dependencia obligatoria `catalog` y sin habilitación silenciosa para empresas existentes. Menú anidado en Catálogo con gate propio; producto conserva su comportamiento.
Entidad Service independiente, UUID, nombre/código/descripción/precio base Decimal/duración entera positiva/especialidad opcional/activo/fechas. Tabla con company_id obligatorio; repositorio acotado por empresa y constraint de código no vacío por empresa, normalizado a mayúsculas por instrucción explícita del usuario. No hay columnas de stock/unidad ni movimientos asociados.
Domain/application/infrastructure/api según patrones existentes. API `/api/services/`, detalle UUID y POST activate/deactivate. Vistas con required_modules=('services',); permiso admin/empresa activa ya existente. Empresa del contexto de sesión; PATCH parcial y sin borrado público. Fachada pública `get_service(company_id, service_id)` retorna DTO inmutable con nombre/precio/duración/activo; consumidores futuros capturan valores, jamás referencian precio/duración vivos como histórico. DTO no altera por sí mismo proformas o citas: su persistencia y pruebas corresponden a PB-COT-001/PB-AGE-002.
Puerto para especialidades con adaptador sobre fachada pública de Personal cuando exista, sin FK/import de modelos ajenos ni tabla duplicada. Rechazar referencias ajenas/inexistentes. No asumir el contrato de una rama ajena como entregado. Se entrega primero sin especialidad: proveedor no disponible rechaza UUID no nulo; null permitido. Integración posterior añade adaptador real sin duplicar datos. No es bloqueo porque la fuente define Personal como opcional.
## Alternativas consideradas
- Product tracks_stock=False: mezcla conceptos, expone usos y carece de duración; descartado.
- Service dentro de catalog sin gate independiente: más simple, pero no cumple la independencia habilitable descrita en especificaciones.
- Crear especialidades propias o implementar Agenda/Cotizaciones ahora: invade historias y duplica propiedad; descartado.
- UUID libre sin validación: viola aislamiento; descartado.
## Estrategia de rollback / mitigación
Migración aditiva, sin modificar tablas ni migraciones aplicadas. Deshabilitar services retira acceso conservando maestros. Rollback de código conserva datos/tablas; no aplicar migración inversa destructiva con datos sin respaldo y decisión operativa. Probar dos empresas, permisos, gates, constraints/concurrencia y contratos. Integraciones consumidoras no se instalan ni se simulan como producto terminado.
## Consecuencias
Agregar app Django, gates, rutas, feature Angular y entrada del mapa de límites. Ninguna dependencia nueva prevista. No alterar pedidos/productos para demostrar un flujo de otro dominio. Código en mayúsculas confirmado por usuario; el resto del diseño deriva de las fuentes y sigue propuesto.
