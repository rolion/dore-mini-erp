import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { MovementReverseDialogComponent } from '../../components/movement-reverse-dialog/movement-reverse-dialog.component';
import { StockAdjustmentDetail, signedDifference } from '../../models/adjustment';
import { InventoryApiError } from '../../models/api-error';
import { MOVEMENT_KIND_LABELS, MOVEMENT_STATUS_LABELS } from '../../models/movement';
import { formatQuantity } from '../../models/stock';
import { AdjustmentsApiService } from '../../services/adjustments-api.service';

/** Detalle de un ajuste: «Revertir» corrige el movimiento vinculado con un contramovimiento. */
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
  successMessage = '';

  private api = inject(AdjustmentsApiService);
  private route = inject(ActivatedRoute);
  private modal = inject(NgbModal);
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

  async reverse(): Promise<void> {
    const adjustment = this.adjustment;
    if (!adjustment || adjustment.status !== 'confirmed') return;
    const ref = this.modal.open(MovementReverseDialogComponent, { backdrop: 'static' });
    (ref.componentInstance as MovementReverseDialogComponent).init({
      id: adjustment.movementId,
      reference: adjustment.reference,
      typeLabel: `${adjustment.kind === 'in' ? 'Entrada' : 'Salida'} de ajuste`,
      productName: adjustment.product.name,
      warehouseName: adjustment.warehouse.name,
      quantity: adjustment.difference.replace(/^-/, ''),
      unitAbbreviation: adjustment.unitAbbreviation,
      kind: adjustment.kind,
    });
    try {
      await ref.result;
    } catch {
      return; // «Volver»: no cambia nada.
    }
    this.successMessage = 'Ajuste revertido';
    this.load();
  }

  display(quantity: string): string {
    return formatQuantity(quantity);
  }

  signed(difference: string): string {
    return signedDifference(difference);
  }
}
