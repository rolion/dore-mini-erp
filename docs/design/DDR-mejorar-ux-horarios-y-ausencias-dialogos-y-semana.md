# DDR-mejorar-ux-horarios-y-ausencias-dialogos-y-semana: Diálogos y vista semanal

**Estado:** Propuesto
**Task relacionado:** TASK-mejorar-ux-horarios-y-ausencias
**Fecha:** 2026-11-04

## Contexto
La pantalla obliga a abrir el diálogo de turno una vez por día y no permite corregir ni quitar una ausencia. Se conserva la estructura de [DDR-configurar-horarios-y-disponibilidad-vista-semanal](DDR-configurar-horarios-y-disponibilidad-vista-semanal.md) (siete grupos por día, `<dialog>` nativo) y se refina.

## Pantallas/flujos afectados
Agenda › Configuración › Horarios y ausencias: tarjeta de cada día, diálogo de turno, diálogo de ausencia.

## Componentes/patrones elegidos
- **Diálogo de turno (alta):** reemplaza el selector «Día» por un grupo de casillas con aspecto de chips (L M X J V S D, `role="group"` con `aria-label`, cada una un `input type=checkbox` con `label`) y atajos «Lun–Vie», «Todos» y «Limpiar» (`btn btn-light btn-sm`). Al menos un día es obligatorio.
- **Repetición:** selector de tres opciones (radio): «Solo esta semana», «Hasta fin de mes» y «Hasta una fecha». Calculan `valid_from` (inicio de la semana visible) y `valid_until`; la fecha final solo aparece en «Hasta una fecha». Debajo, una línea de resumen (`small.text-muted`): «Lun a Vie, 08:00–20:00, del 02/11/2026 al 30/11/2026».
- **Edición de un turno:** un solo día (los chips actúan como selección única) y vigencia con las mismas opciones. «Copiar a otros días» en cada turno abre el alta con horario, pausas y vigencia precargados y ningún día marcado (el día original queda deshabilitado).
- **Diálogo de ausencia:** interruptor «Todo el día» (`form-check form-switch`); activado muestra solo fechas «Desde/Hasta» (inclusivas); desactivado muestra fecha y hora. Duración calculada en línea («2 días»). Misma pantalla para crear y editar.
- **Tarjeta de día:** cada ausencia es un renglón compacto «Ausente · motivo» con acciones «Editar» y «Eliminar» (`btn btn-link`, texto visible). Las ausencias de varios días muestran el rango completo solo en el diálogo.
- **Eliminar ausencia:** confirmación en el mismo diálogo (patrón «acción irreversible», sin motivo): «¿Eliminar la ausencia? El horario volverá a estar disponible».
- **Cabecera:** «Nuevo turno» (`btn-primary`, única acción principal) y «Registrar ausencia» (`btn-light`) suben junto a la navegación de semana. Los mensajes de éxito pasan a aviso `alert-success` descartable bajo la cabecera sin empujar el contenido (se mantiene `role="status"`).
- Botón secundario y Cancelar en `btn-light`; guardar se deshabilita durante el envío.

## Alternativas consideradas
1. Selector múltiple desplegable de días: menos visible y peor en móvil. Descartada.
2. Grilla semanal interactiva: gran esfuerzo y ya descartada en el DDR anterior.
3. Crear en un diálogo y copiar desde la tarjeta de cada día: se incluye solo «Copiar a otros días» como complemento.

## Comportamiento por privilegio/estado
Cargando, vacío, error con reintento y éxito como hoy. Errores del servidor (400 por solape o fechas) en `alert-danger` dentro del diálogo y sin perder lo escrito. El backend exige empresa, módulos Personal y Agenda y valida solapes; el frontend no es la barrera.

## Consecuencias
La alta masiva muestra el primer error de solape indicando el día afectado y no crea ninguno. Sigue sin haber borrado de turnos (deuda aceptada: se corrige editando su vigencia). El diálogo usa `<dialog>` nativo, no `NgbModal` (consistencia con la pantalla existente).
