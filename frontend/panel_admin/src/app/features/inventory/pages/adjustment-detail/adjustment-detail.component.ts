import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { StockAdjustmentDetail, signedDifference } from '../../models/adjustment';
import { InventoryApiError } from '../../models/api-error';
import { MOVEMENT_KIND_LABELS, MOVEMENT_STATUS_LABELS } from '../../models/movement';
import { formatQuantity } from '../../models/stock';
import { AdjustmentsApiService } from '../../services/adjustments-api.service';

/** Detalle de un ajuste confirmado: solo lectura. «Revertir» llega con PB-INV-008 y por ahora no se ofrece. */
@Component({
  selector: 'app-adjustment-detail',
  templateUrl: './adjustment-detail.component.html',
  imports: [RouterLink, DatePipe],
})
export class AdjustmentDetailComponent implements OnInit {
  readonly kindLabels = MOVEMENT_KIND_LABELS;
  readonly statusLabels = MOVEMENT_STATUS_LABELS;

  adjustment: StockAdjustmentDetail | null = null;
  loading = true;
  errorMessage = '';
  notFound = false;

  private api = inject(AdjustmentsApiService);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.errorMessage = '';
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.api
      .get(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (adjustment) => {
          this.adjustment = adjustment;
          this.loading = false;
        },
        error: (err: InventoryApiError) => {
          this.loading = false;
          this.notFound = err.status === 404;
          this.errorMessage = err.message;
        },
      });
  }

  display(quantity: string): string {
    return formatQuantity(quantity);
  }

  signed(difference: string): string {
    return signedDifference(difference);
  }
}
