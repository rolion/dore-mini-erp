import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import {
  DOCUMENTAL_LABEL,
  REVERT_REASON_MAX_LENGTH,
  Receipt,
  ReceiptApiError,
  ReceiptShortage,
  SIN_ENTRADA_LABEL,
} from '../../models/receipt';
import { ReceiptsApiService } from '../../services/receipts-api.service';

/**
 * Reversión de una recepción completa (sin reversión parcial): lista todas sus líneas y el impacto, avisa que no
 * devuelve pagos y exige un motivo. Se cierra devolviendo la recepción revertida; los errores del servidor quedan
 * dentro del diálogo sin perder el motivo escrito.
 */
@Component({
  selector: 'app-receipt-revert-dialog',
  templateUrl: './receipt-revert-dialog.component.html',
  imports: [ReactiveFormsModule],
})
export class ReceiptRevertDialogComponent {
  readonly maxLength = REVERT_REASON_MAX_LENGTH;
  readonly documentalLabel = DOCUMENTAL_LABEL;
  readonly noEntryLabel = SIN_ENTRADA_LABEL;
  readonly form = inject(FormBuilder).nonNullable.group({ reason: '' });
  readonly activeModal = inject(NgbActiveModal);
  receipt: Receipt | null = null;
  saving = false;
  reasonError = '';
  errorMessage = '';
  shortage: ReceiptShortage | null = null;

  private api = inject(ReceiptsApiService);
  private destroyRef = inject(DestroyRef);

  init(receipt: Receipt): void {
    this.receipt = receipt;
  }

  get reason(): string {
    return this.form.controls.reason.value.trim();
  }

  get canSubmit(): boolean {
    return !this.saving && this.reason.length > 0 && this.reason.length <= this.maxLength;
  }

  submit(): void {
    const receipt = this.receipt;
    if (!receipt || !this.canSubmit) return;
    this.saving = true;
    this.reasonError = '';
    this.errorMessage = '';
    this.shortage = null;
    this.api
      .revert(receipt.purchase.id, receipt.id, this.reason)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (reverted) => this.activeModal.close(reverted),
        error: (err: ReceiptApiError) => {
          this.saving = false;
          this.reasonError = err.fieldErrors.reason ?? '';
          this.shortage = err.shortage;
          this.errorMessage = this.reasonError || this.shortage ? '' : err.message;
        },
      });
  }
}
