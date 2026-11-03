# Límites de Agenda y referencia temporal

**Estado:** Propuesto
**Task relacionado:** TASK-configurar-horarios-y-disponibilidad
**Fecha:** 2026-11-03

Agenda posee turnos, pausas y ausencias. Un contrato de aplicación de Personal comprueba el profesional por empresa e identificador. Usar tablas de Personal directamente acoplaría la persistencia de ambos módulos. La empresa se obtiene de sesión y el backend exige Personal y Agenda habilitados.

Centralizar la zona `America/La_Paz` en Agenda y devolver su identificador en la consulta semanal. Persistir horas de recurrencia como hora civil y ausencias como instantes con zona. Los turnos terminan el mismo día. El servidor calcula la semana en esa zona. Esta política evita cambiar el significado del ajuste global de Django y permite introducir una fuente por empresa más adelante.

Serializar escrituras con un registro de bloqueo propio de Agenda por empresa y profesional, único en la base. Validar solapamientos dentro de la misma transacción que escribe. La migración es aditiva. Ante una incidencia, deshabilitar Agenda por empresa y conservar las tablas hasta decidir cómo recuperar los datos.
