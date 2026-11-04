import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { InsufficientStockInfo, InventoryApiError } from '../../models/api-error';
import { MovementKind, REVERSAL_REASON_MAX_LENGTH, StockMovementDetail } from '../../models/movement';
import { MovementsApiService } from '../../services/movements-api.service';
import { InsufficientStockAlertComponent } from '../insufficient-stock-alert/insufficient-stock-alert.component';

/** Datos del movimiento que se muestra en el diálogo antes de revertirlo. */
export interface ReversibleMovement {
  id: string;
  reference: string;
  typeLabel: string;
  productName: string;
  warehouseName: string;
  /** Cantidad sin signo (decimal como texto). */
  quantity: string;
  unitAbbreviation: string | null;
  kind: MovementKind;
}

/**
 * Reversión de un movimiento manual: muestra el efecto inverso previsto y exige un motivo. Se cierra devolviendo el
 * contramovimiento creado; los errores del servidor se muestran dentro del diálogo sin perder el motivo escrito.
 */
@Component({
  selector: 'app-movement-reverse-dialog',
  templateUrl: './movement-reverse-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, InsufficientStockAlertComponent],
})
export class MovementReverseDialogComponent {
  readonly maxLength = REVERSAL_REASON_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group({ reason: '' });
  readonly activeModal = inject(NgbActiveModal);
  movement: ReversibleMovement | null = null;
  saving = false;
  reasonError = '';
  errorMessage = '';
  stockShortage: InsufficientStockInfo | null = null;

  private api = inject(MovementsApiService);
  private destroyRef = inject(DestroyRef);

  init(movement: ReversibleMovement): void {
    this.movement = movement;
  }

  get reason(): string {
    return this.form.controls.reason.value.trim();
  }

  get canSubmit(): boolean {
    return !this.saving && this.reason.length > 0 && this.reason.length <= this.maxLength;
  }

  /** Efecto inverso: la reversión de una entrada es una salida y viceversa. */
  get effect(): string {
    const movement = this.movement;
    if (!movement) return '';
    const inverse = movement.kind === 'in' ? tr('COMMON.AN_OUTBOUND') : tr('COMMON.AN_INBOUND');
    const unit = movement.unitAbbreviation ? ` ${movement.unitAbbreviation}` : '';
    return tr('INVENTORY.MOVEMENT_REVERSE_DIALOG.SE_REGISTRARA_DE_EN', { p0: inverse, p1: movement.quantity, p2: unit, p3: movement.warehouseName });
  }

  submit(): void {
    const movement = this.movement;
    if (!movement || !this.canSubmit) return;
    this.saving = true;
    this.reasonError = '';
    this.errorMessage = '';
    this.stockShortage = null;
    this.api
      .reverse(movement.id, this.reason)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (counter: StockMovementDetail) => this.activeModal.close(counter),
        error: (err: InventoryApiError) => {
          this.saving = false;
          this.reasonError = err.fieldErrors['reason']?.join(' ') ?? '';
          this.stockShortage = err.insufficientStock;
          this.errorMessage = this.reasonError || this.stockShortage ? '' : err.message;
        },
      });
  }
}
