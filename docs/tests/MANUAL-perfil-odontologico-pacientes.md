# Recorrido PB-ODO-001

Usar datos ficticios, una empresa con Clientes y Odontología habilitados y admin con sesión. Odontología viene deshabilitada por defecto. No registrar información clínica real para validar.

| Paso | Resultado esperado | AC |
|---|---|---|
| Abrir Odontología → Pacientes sin perfiles | Vacío explicado y alta disponible | 07/08 |
| Buscar/seleccionar cliente o crearlo desde el flujo existente | Mantiene ID; coincidencias de teléfono usan advertencia existente | 01 |
| Seleccionar cliente con perfil | Ofrece abrir ficha y bloquea crear duplicado | 01 |
| Crear perfil de un cliente sin perfil | Ficha con Perfil y Antecedentes; sin pestañas futuras | 01/07 |
| Perfil: fecha desconocida | No supone mayoría de edad; campos opcionales | 04 |
| Perfil: nacimiento menor de 18, sin responsable | Nombre/teléfono requeridos; no guarda | 04 |
| Añadir responsable, guardar | Éxito e historial administrativo con autor/fecha/antes/después | 04/05 |
| Abrir Antecedentes | Blanco = No informado, no ausencia; solo aquí aparecen datos clínicos | 02/03 |
| Escribir antecedentes, guardar, editar, borrar texto | Historial clínico conserva versiones; vacío vuelve a No informado | 02/05 |
| Editar ambos formularios, guardar solo uno | El otro borrador se conserva; salir pide confirmación | 08 |
| Simular fallo API al guardar | Mensaje visible, datos conservados y doble envío bloqueado | 08 |
| Archivar con confirmación | Conserva historia/cliente; perfil de solo lectura; no permite duplicarlo | 06 |
| Filtrar Archivados y reactivar | Mismo ID e historial, editable de nuevo | 06/07 |
| Buscar, paginar y volver desde ficha | Conserva filtros/página | 07 |
| Deshabilitar Odontología y abrir URL directa | Módulo no habilitado; API rechaza clínica | 03 |
| Otro admin de otra empresa abre ID/historial | 404 sin fuga | 03 |
| Revisar a 390 y 1440 px, claro/oscuro y teclado | Sin solapamiento; formularios/tabla usables, labels y foco | 08 |

No se crean roles Profesional/Recepción ni se prueba agenda inexistente. La denegación a roles no autorizados y la política clínica explícita se cubren en integración API.
