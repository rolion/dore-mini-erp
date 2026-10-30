import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import {
  DOCUMENTAL_LABEL,
  RECEIPT_STATUS_CLASSES,
  RECEIPT_STATUS_LABELS,
  Receipt,
  ReceiptApiError,
  SIN_ENTRADA_LABEL,
} from '../../models/receipt';
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

  private api = inject(ReceiptsApiService);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);

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
