import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject, input } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { RECEPTION_STATUS_LABELS, Purchase } from '../../models/purchase';
import {
  RECEIPT_STATUS_CLASSES,
  RECEIPT_STATUS_LABELS,
  ReceiptApiError,
  ReceiptSummary,
} from '../../models/receipt';
import { ReceiptsApiService } from '../../services/receipts-api.service';

/** Pestaña «Recepciones» de la compra: avance por producto y recepciones registradas. */
@Component({
  selector: 'app-purchase-receipts-tab',
  templateUrl: './purchase-receipts-tab.component.html',
  imports: [RouterLink, DatePipe],
})
export class PurchaseReceiptsTabComponent implements OnInit {
  readonly purchase = input.required<Purchase>();
  readonly receptionLabels = RECEPTION_STATUS_LABELS;
  readonly statusLabels = RECEIPT_STATUS_LABELS;
  readonly statusClasses = RECEIPT_STATUS_CLASSES;
  receipts: ReceiptSummary[] = [];
  loading = true;
  errorMessage = '';

  private api = inject(ReceiptsApiService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.load();
  }

  get isConfirmed(): boolean {
    return this.purchase().status === 'confirmed';
  }

  get canReceive(): boolean {
    return this.purchase().allowedActions.includes('receive');
  }

  load(): void {
    this.loading = true;
    this.errorMessage = '';
    this.api
      .list(this.purchase().id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (page) => {
          this.receipts = page.results;
          this.loading = false;
        },
        error: (err: ReceiptApiError) => {
          this.errorMessage = err.message;
          this.loading = false;
        },
      });
  }
}
