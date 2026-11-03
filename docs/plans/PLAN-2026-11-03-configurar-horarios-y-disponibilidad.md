# PB-AGE-001 · Configurar horarios y disponibilidad

**Versión:** v1
**Modo:** COMPLETO
**Specification readiness:** READY

## Specification

- AC-01. Un administrador con Personal y Agenda habilitados puede seleccionar un profesional de su empresa, crear y editar turnos semanales y registrar ausencias. La API rechaza referencias ajenas y aplica empresa y permisos en cada operación.
- AC-02. El turno tiene día, inicio y fin locales, vigencia por fechas inclusivas y pausas dentro del turno. Fin posterior al inicio en el mismo día. Rechazar turnos con horas solapadas cuando sus vigencias contienen una ocurrencia común. Los extremos contiguos se permiten. Las pausas son intervalos disjuntos.
- AC-03. La ausencia tiene inicio y fin con fecha y hora y motivo administrativo. Fin posterior al inicio. La disponibilidad resulta de descontar la unión de pausas y ausencias a los turnos vigentes. Para un turno 09:00–12:00 con ausencia 10:00–11:00, quedan 09:00–10:00 y 11:00–12:00.
- AC-04. La vista semanal usa la zona Bolivia (`America/La_Paz`) y distingue intervalos con texto. Carga, vacío, error y éxito visibles. Operación con teclado y conservación de datos ante fallos.
- PB-AGE-002 integrará reservas y conflictos por citas futuras. Configurar zona por empresa, sucursales y recursos físicos queda fuera.

## Test Specification

| Criterio | Verificación |
|---|---|
| AC-01 | Integración API con empresas distintas, módulos deshabilitados y usuario sin autorización. Alta, edición y consulta semanal. |
| AC-02 | Dominio con vigencias adyacentes y coincidentes, extremos contiguos, pausas inválidas y 22:00–02:00. Integración de escrituras simultáneas con solapamiento. |
| AC-03 | Dominio con ausencia central, ausencia de varios días y ausencias superpuestas. API con conversión desde la zona de Agenda. |
| AC-04 | Compilación Angular y recorrido local de selección, semana, formularios, teclado y fallo de guardado. |

Pruebas E2E automatizadas aplazadas hasta el flujo de reserva. No se prevén nuevas dependencias.

## Implementation Plan

1. Registrar Agenda y crear dominio, modelos y migración aditiva. Incorporar contrato público de Personal y repositorios acotados por empresa.
2. Exponer bajo `/api/agenda/` consulta semanal por profesional y fecha de inicio de semana, creación y actualización de turnos y registro de ausencias. La consulta devuelve zona, turnos, pausas, ausencias e intervalos disponibles. Validar forma de datos en serializers y reglas temporales en dominio.
3. Incorporar navegación condicionada por los módulos y vista Angular con formularios reactivos. Aplicar el [DDR](../design/DDR-configurar-horarios-y-disponibilidad-vista-semanal.md) y el [ADR](../adr/ADR-configurar-horarios-y-disponibilidad-limites-y-tiempo.md).
4. Ejecutar las verificaciones de la Test Specification y documentar resultados y diferencias de implementación.
