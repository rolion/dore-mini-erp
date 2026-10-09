import { DatePipe } from '@angular/common';
import { Component, inject, input, output } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { DEFAULT_SELECTION, Period, PeriodSelection, isRangeValid } from '../../models/report';

export type SelectorKind = 'day' | 'week' | 'month' | 'range';

export const SELECTOR_OPTIONS: readonly { kind: SelectorKind; label: string }[] = [
  { kind: 'day', label: 'Hoy' },
  { kind: 'week', label: 'Esta semana' },
  { kind: 'month', label: 'Este mes' },
  { kind: 'range', label: 'Rango' },
];

export const INVALID_RANGE_MESSAGE = 'Elige las dos fechas; la final no puede ser anterior a la inicial.';

/**
 * Selector de periodo compartido por el dashboard y los reportes. No calcula fechas: emite lo pedido y muestra
 * las fechas efectivas que devuelve el servidor (así "semana" y "mes" nunca son ambiguos).
 */
@Component({
  selector: 'app-period-selector',
  templateUrl: './period-selector.component.html',
  imports: [ReactiveFormsModule, DatePipe],
})
export class PeriodSelectorComponent {
  /** Periodo efectivo de la última respuesta del servidor; `null` mientras no se conoce. */
  readonly effective = input<Period | null>(null);
  readonly selectionChange = output<PeriodSelection>();

  readonly options = SELECTOR_OPTIONS;
  readonly rangeForm = inject(FormBuilder).nonNullable.group({ dateFrom: [''], dateTo: [''] });

  kind: SelectorKind = DEFAULT_SELECTION.kind;
  rangeError = '';

  select(kind: SelectorKind): void {
    this.kind = kind;
    this.rangeError = '';
    if (kind !== 'range') {
      this.selectionChange.emit({ kind });
    }
  }

  applyRange(): void {
    const { dateFrom, dateTo } = this.rangeForm.getRawValue();
    if (!isRangeValid(dateFrom, dateTo)) {
      this.rangeError = INVALID_RANGE_MESSAGE;
      return;
    }
    this.rangeError = '';
    this.selectionChange.emit({ kind: 'range', dateFrom, dateTo });
  }
}
