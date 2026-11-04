# DDR-proformas-odontologicas-con-pieza-dental-proformas-en-ficha-del-paciente: Proformas en la ficha del paciente

**Estado:** Propuesto
**Task relacionado:** TASK-proformas-odontologicas-con-pieza-dental
**Fecha:** 2026-11-04

## Contexto
El doctor elabora proformas dentro de Odontología indicando en cada línea la pieza dental, y consulta desde la ficha del paciente todas sus proformas con su estado. La interfaz del módulo genérico (DDR de PB-COT-001) es la base.

## Pantallas/flujos afectados
- **Ficha del paciente** (`/pocketbiz/dentistry/patients/:id`): nueva tarjeta **«Proformas»** (visible solo con `services` habilitado) con tabla Número/versión · Fecha · Total propuesto · Estado (badge con texto) · «Ver detalle», más botón «Nueva proforma». Estados cargando, vacío («Este paciente aún no tiene proformas»), error con «Reintentar» y paginación simple (Anterior/Siguiente). Va después de los datos clínicos y antes del historial.
- **Nueva / editar proforma** (`/pocketbiz/dentistry/patients/:id/proformas/nueva` y `/pocketbiz/dentistry/proformas/:id/editar`): formulario como el genérico con el paciente fijo en la cabecera (solo lectura). La tabla de líneas añade la columna **«Pieza dental»**: input de texto opcional, `maxlength` 20, `aria-label` por línea, error por línea; para líneas ya guardadas se conserva y se puede editar mientras la proforma sea borrador.
- **Detalle** (`/pocketbiz/dentistry/proformas/:id`): como el genérico; la tabla de líneas muestra la pieza («—» si no hay); versiones y acciones Editar / Presentar / Nueva versión según `allowed_actions`; diálogo de presentar. Enlace de regreso a la ficha del paciente.
- No hay menú global de proformas de Odontología en esta historia.

## Componentes/patrones elegidos
`design-system.md` §5: Lista con filtros (reducida a tabla en tarjeta), Formulario, Detalle con acciones; badges `col-orange` borrador, `col-blue` presentada, `col-grey` reemplazada; `MoneyPipe`; fechas `dd/MM/yyyy`; `unsavedChangesGuard` en el formulario; diálogo nativo `<dialog>` con Escape bloqueado al guardar. Textos con `translate`/`tr()` bajo `DENTISTRY.PROFORMAS.*` (es/en/pt). La tabla de líneas se copia del feature `quotations` (instrucción del usuario); no se crean componentes compartidos.

## Alternativas consideradas
- Pestañas dentro de la ficha: la ficha actual no usa pestañas; una tarjeta es más consistente y barata.
- Pieza en un selector de odontograma: no existe odontograma; texto libre pedido por el usuario.

## Comportamiento por privilegio/estado
Solo administradores con acceso clínico (`clinicalGuard`). Paciente archivado: la lista se muestra, «Nueva proforma» y las acciones de edición están deshabilitadas con explicación. Sin `services` habilitado la tarjeta no aparece. **El backend aplica empresa, módulos, perfil activo, permiso de precio y recálculo**; el frontend no es la barrera.

## Consecuencias
Duplicación de UI con `quotations` aceptada. La ficha del paciente crece en una tarjeta; sin vista global de proformas dentales.
