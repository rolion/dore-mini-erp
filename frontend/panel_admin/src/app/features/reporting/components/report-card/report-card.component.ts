import { Component, input, output } from '@angular/core';

/**
 * Tarjeta de un informe que carga y falla por su cuenta: muestra "Cargando…", el error con "Reintentar" o, cuando
 * está lista, el contenido proyectado.
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
  readonly retry = output<void>();
}
