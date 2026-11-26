import { Component, computed, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { ModulesService } from '../../../../core/service/modules.service';

/** Códigos 409 con los que el servidor bloquea confirmar un pedido por su período fiscal. */
export const FISCAL_PERIOD_ERROR_CODES = ['fiscal_period_missing', 'fiscal_period_closed'] as const;
export type FiscalPeriodErrorCode = (typeof FISCAL_PERIOD_ERROR_CODES)[number];

export function isFiscalPeriodErrorCode(code: string): code is FiscalPeriodErrorCode {
  return (FISCAL_PERIOD_ERROR_CODES as readonly string[]).includes(code);
}

/**
 * Aviso del bloqueo al confirmar un pedido cuya fecha no tiene período fiscal abierto (DDR numeración correlativa).
 * Presentacional: el bloqueo lo impone el servidor; el enlace a Contabilidad solo aparece si el módulo está habilitado.
 */
@Component({
  selector: 'app-fiscal-period-alert',
  imports: [RouterLink, TranslatePipe],
  template: `
    <div class="alert alert-warning bg-warning-subtle text-warning-emphasis border-warning-subtle mb-3" role="alert"
         data-testid="alert-fiscal-period">
      <span data-testid="fiscal-period-message">{{ messageKey() | translate: { name: periodName() } }}</span>
      @if (accountingEnabled()) {
        <a routerLink="/pocketbiz/accounting/settings" [queryParams]="{ tab: 'periods' }"
           class="ms-1 text-reset text-decoration-underline" data-testid="fiscal-period-link">{{ 'SALES.FISCAL_PERIOD.IR_A_PERIODOS' | translate }}</a>
      }
    </div>
  `,
})
export class FiscalPeriodAlertComponent {
  private readonly modules = inject(ModulesService);

  readonly code = input.required<FiscalPeriodErrorCode>();
  /** Nombre del período cerrado (si el servidor lo informó): el aviso lo nombra. */
  readonly periodName = input<string>('');

  readonly messageKey = computed(() => {
    if (this.code() !== 'fiscal_period_closed') return 'SALES.FISCAL_PERIOD.SIN_PERIODO';
    return this.periodName() ? 'SALES.FISCAL_PERIOD.CERRADO_NOMBRE' : 'SALES.FISCAL_PERIOD.CERRADO';
  });

  accountingEnabled(): boolean {
    return this.modules.enabledKeysValue?.has('accounting') ?? false;
  }
}
