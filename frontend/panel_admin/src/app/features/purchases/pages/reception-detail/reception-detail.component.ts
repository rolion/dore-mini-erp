import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import {
  DOCUMENTAL_LABEL,
  RECEIPT_STATUS_CLASSES,
  RECEIPT_STATUS_LABELS,
  Receipt,
  ReceiptApiError,
  SIN_ENTRADA_LABEL,
} from '../../models/receipt';
import { ReceiptRevertDialogComponent } from '../../components/receipt-revert-dialog/receipt-revert-dialog.component';
import { ReceiptsApiService } from '../../services/receipts-api.service';

/** Detalle de una recepción: productos recibidos, almacén y movimientos de inventario vinculados. */
@Component({
  selector: 'app-reception-detail',
  templateUrl: './reception-detail.component.html',
  imports: [RouterLink, DatePipe],
})
export class ReceptionDetailComponent implements OnInit {
  readonly statusLabels = RECEIPT_STATUS_LABELS;
  readonly statusClasses = RECEIPT_STATUS_CLASSES;
  readonly documentalLabel = DOCUMENTAL_LABEL;
  readonly noEntryLabel = SIN_ENTRADA_LABEL;
  purchaseId = '';
  receipt: Receipt | null = null;
  loading = true;
  errorMessage = '';
  successMessage = '';

  private api = inject(ReceiptsApiService);
  private route = inject(ActivatedRoute);
  private modal = inject(NgbModal);
  private destroyRef = inject(DestroyRef);

  /** Por qué una recepción confirmada no se puede revertir (Inventario deshabilitado tras mover stock). */
  get revertBlockedMessage(): string {
    const receipt = this.receipt;
    return receipt?.status === 'confirmed' && !receipt.canRevert
      ? 'Inventario está deshabilitado: habilítalo para revertir una recepción que movió existencias.'
      : '';
  }

  async revert(): Promise<void> {
    const receipt = this.receipt;
    if (!receipt?.canRevert) return;
    const ref = this.modal.open(ReceiptRevertDialogComponent, { backdrop: 'static' });
    (ref.componentInstance as ReceiptRevertDialogComponent).init(receipt);
    try {
      await ref.result;
    } catch {
      return; // «Volver»: no cambia nada.
    }
    this.successMessage = 'Recepción revertida';
    this.load();
  }

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    const params = this.route.snapshot.paramMap;
    this.purchaseId = params.get('id') ?? '';
    this.loading = true;
    this.errorMessage = '';
    this.api
      .get(this.purchaseId, params.get('receiptId') ?? '')
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (receipt) => {
          this.receipt = receipt;
          this.loading = false;
        },
        error: (err: ReceiptApiError) => {
          this.errorMessage = err.message;
          this.loading = false;
        },
      });
  }
}
