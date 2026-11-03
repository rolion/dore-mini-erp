import { tr } from '../../core/i18n/translate';
import { Pipe, PipeTransform } from '@angular/core';

/** Muestra un importe tal como lo entrega el servidor ("70.00" → "Bs 70.00"); no convierte ni redondea. */
@Pipe({ name: 'money' })
export class MoneyPipe implements PipeTransform {
  transform(value: string | null | undefined): string {
    return value ? tr('SHARED.MONEY_PIPE.BS', { p0: value }) : '—';
  }
}
