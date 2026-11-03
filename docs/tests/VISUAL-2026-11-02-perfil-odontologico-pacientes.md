# Revisión visual PB-ODO-001 — 2026-11-02

**Código:** b0086a9 · **Revisor visual:** orquestador delivery-publish · **Datos:** exclusivamente ficticios.

Se usó Browser Use en el navegador integrado contra el build de producción del worktree, servido en `http://127.0.0.1:4208`, con API temporal en 8017 y PostgreSQL aislado en 55433. No se utilizó la base existente ni se leyó `.env`. El servidor Vite no fue la fuente de esta revisión: sus dependencias enlazadas entre discos producen un fallo específico del entorno Windows.

## Resultado observado

| Superficie | Evidencia observada |
|---|---|
| Lista, escritorio 1440 px | Estado vacío explicado, búsqueda/filtro, alta y tabla. Con perfil existente: nombre, teléfono, estado y enlace a ficha. El build final conserva Dashboard primero y coloca Odontología después de Clientes. |
| Alta | Selección del Customer ficticio existente; crea ficha usando el mismo UUID. No crea otro cliente. |
| Perfil | Datos administrativos separados; nacimiento 01/01/2010 exige nombre y teléfono del responsable; Guardar bloqueado hasta completar ambos. Guardado exitoso visible. |
| Antecedentes | Cinco campos opcionales, vacíos como No informado. Guardado de texto ficticio con confirmación visible; historial muestra autor, fecha, antes/después. |
| Historial final | Nacimiento se visualiza `01/01/2010`; fechas de eventos `02/11/2026 HH:mm`. |
| Móvil 390 × 844 | Capturas de Perfil y Antecedentes inspeccionadas: campos apilados y texto legible, sin solapamientos. Lectura DOM estable: `innerWidth=390`, `documentElement.scrollWidth=375`, `body.scrollWidth=375`. |
| Tablas de historial en móvil | Scroll horizontal dentro de `.table-responsive` (`overflowX=auto`, `scrollWidth=800`, `clientWidth=183`), sin ensanchar la página. |
| Temas | Claro y oscuro inspeccionados en escritorio/móvil; campos, pestañas y estados conservan contraste y clases de la plantilla. El cambio de tema se hizo en la sesión ficticia; no se modificó configuración de producto. |
| Archivo | Diálogo nativo visible: «¿Archivar el perfil? Se conservará su historia y el cliente seguirá disponible.» La herramienta no conservó el diálogo para aceptarlo; no se afirma archivo ejecutado en navegador. La transición, conservación y reactivación se verifican en API y componentes automatizados. |

Las capturas fueron emitidas como imágenes nativas en el chat durante la inspección; no se incorporaron imágenes ni datos de personas reales al repositorio. Revisión estática complementaria: labels asociados, botones con nombres accesibles, guard de salida con cambios, sin HEX ni fuentes propios y sin capacidades futuras aparentando estar implementadas. El Quality Gate técnico independiente se documenta por separado.
