# Vista semanal de horarios y ausencias

**Estado:** Propuesto
**Task relacionado:** TASK-configurar-horarios-y-disponibilidad
**Fecha:** 2026-11-03

Agenda → Configuración → Horarios y Ausencias. La tarjeta de configuración sigue la sección 5 del [sistema de diseño](design-system.md). Muestra selector de profesional, semana anterior/siguiente y rango en hora de Bolivia. Dentro de la tarjeta, siete grupos por día muestran intervalos con texto «Disponible», «Pausa» y «Ausencia». Los grupos se apilan en pantallas estrechas. Se prefiere esta estructura a una grilla interactiva porque permite leer los intervalos y operar las acciones con controles nativos.

Los formularios de turno y ausencia usan los patrones de formulario y diálogo de configuración. El turno recoge día, horas, vigencia y pausas. Si el fin es igual o anterior al inicio, el error indica que debe terminar ese día. La ausencia recoge fecha y hora de inicio y fin y motivo. Conservar entradas ante errores, enfocar el error pertinente y deshabilitar el guardado durante el envío. Mostrar carga, vacío, error con reintento y éxito. La navegación requiere Agenda habilitada y acceso administrativo. El backend valida ambos requisitos.
