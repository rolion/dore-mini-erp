import { Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';

/** Códigos de error de la API cuando falta o no sirve la clasificación de egreso (CONT-03). */
export const CLASSIFICATION_ERROR_CODES: readonly string[] = ['classification_not_configured', 'classification_invalid'];

export function isClassificationErrorCode(code: string | null | undefined): boolean {
  return !!code && CLASSIFICATION_ERROR_CODES.includes(code);
}

/** Enlace de ayuda «Configurar en Contabilidad → Egresos»; solo aparece con uno de los códigos anteriores. */
@Component({
  selector: 'app-classification-hint',
  imports: [RouterLink, TranslatePipe],
  template: `
    @if (visible()) {
    <a class="d-inline-block mt-1" routerLink="/pocketbiz/accounting/settings/legacy" [queryParams]="{ tab: 'expenses' }" data-testid="classification-hint" (click)="followed.emit()">
      {{ 'ACCOUNTING.EXPENSE_CONFIG.CONFIGURAR_EN_CONTABILIDAD' | translate }}
    </a>
    }
  `,
})
export class ClassificationHintComponent {
  readonly code = input<string | null>(null);
  /** Se emite al pulsar el enlace (p. ej. para cerrar un diálogo antes de navegar). */
  readonly followed = output<void>();

  visible(): boolean {
    return isClassificationErrorCode(this.code());
  }
}
