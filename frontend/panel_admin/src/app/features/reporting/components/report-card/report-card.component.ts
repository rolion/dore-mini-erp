import { Component, input, output } from '@angular/core';

/** Texto de una tarjeta cuya fuente (módulo) está deshabilitada: se explica la ausencia, no se muestra cero. */
export const UNAVAILABLE_MESSAGE = 'No disponible: módulo deshabilitado';

/**
 * Tarjeta de un informe que carga y falla por su cuenta: muestra "Cargando…", el error con "Reintentar" o, cuando
 * está lista, el contenido proyectado. Con `unavailable` no pide ni muestra datos: dice que el módulo está deshabilitado.
 */
@Component({
  selector: 'app-report-card',
  templateUrl: './report-card.component.html',
})
export class ReportCardComponent {
  readonly title = input.required<string>();
  readonly status = input.required<'loading' | 'ready' | 'error'>();
  readonly error = input('');
  readonly subtitle = input('');
  /** La fuente de la tarjeta está deshabilitada. */
  readonly unavailable = input(false);
  readonly unavailableMessage = UNAVAILABLE_MESSAGE;
  readonly retry = output<void>();
}
