import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { Observable, finalize } from 'rxjs';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { PurchaseCancelDialogComponent } from '../../components/purchase-cancel-dialog/purchase-cancel-dialog.component';
import { PurchaseConfirmDialogComponent } from '../../components/purchase-confirm-dialog/purchase-confirm-dialog.component';
import {
  PAYMENT_STATUS_LABELS,
  PURCHASE_STATUS_CLASSES,
  PURCHASE_STATUS_LABELS,
  Purchase,
  PurchaseAction,
  PurchaseApiError,
  PurchaseStatus,
  RECEPTION_STATUS_LABELS,
} from '../../models/purchase';
import { PurchasesApiService } from '../../services/purchases-api.service';

/** Detalle de una compra (pestaña «Resumen»): desde aquí se edita, confirma o cancela según el estado. */
@Component({
  selector: 'app-purchase-detail',
  templateUrl: './purchase-detail.component.html',
  imports: [RouterLink, DatePipe, MoneyPipe],
})
export class PurchaseDetailComponent implements OnInit {
  readonly statusLabels = PURCHASE_STATUS_LABELS;
  readonly receptionLabels = RECEPTION_STATUS_LABELS;
  readonly paymentLabels = PAYMENT_STATUS_LABELS;
  purchase: Purchase | null = null;
  loading = true;
  /** Hay una acción de ciclo de vida en curso. */
  busy = false;

  private api = inject(PurchasesApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private modal = inject(NgbModal);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.load();
  }

  statusClass(status: PurchaseStatus): string {
    return PURCHASE_STATUS_CLASSES[status];
  }

  /** El servidor decide qué acciones existen; aquí solo se refleja. */
  can(action: PurchaseAction): boolean {
    return !!this.purchase?.allowedActions.includes(action);
  }

  async confirm(): Promise<void> {
    const purchase = this.purchase;
    if (!purchase || this.busy) return;
    const ref = this.modal.open(PurchaseConfirmDialogComponent, { size: 'lg', backdrop: 'static' });
    (ref.componentInstance as PurchaseConfirmDialogComponent).init(purchase);
    try {
      if ((await ref.result) === true) this.run(this.api.confirm(purchase.id), 'Compra confirmada');
    } catch {
      // «Volver»: no cambia nada.
    }
  }

  async cancel(): Promise<void> {
    const purchase = this.purchase;
    if (!purchase || this.busy) return;
    const ref = this.modal.open(PurchaseCancelDialogComponent, { backdrop: 'static' });
    (ref.componentInstance as PurchaseCancelDialogComponent).init(purchase);
    try {
      const reason = (await ref.result) as string;
      this.run(this.api.cancel(purchase.id, reason), 'Compra cancelada');
    } catch {
      // «Volver»: no cambia nada.
    }
  }

  private run(action: Observable<Purchase>, successMessage: string): void {
    this.busy = true;
    action
      .pipe(
        finalize(() => (this.busy = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (purchase) => {
          this.purchase = purchase;
          this.toastr.success(successMessage);
        },
        error: (err: PurchaseApiError) => {
          this.toastr.error(err.message);
          // Si la compra cambió en otra parte (409/400), se vuelve a leer para reflejar el estado real.
          if (err.status === 409 || err.status === 400) this.reload();
        },
      });
  }

  private reload(): void {
    this.api
      .get(this.purchase?.id ?? '')
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: (purchase) => (this.purchase = purchase), error: () => undefined });
  }

  private load(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.api
      .get(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (purchase) => {
          this.purchase = purchase;
          this.loading = false;
        },
        error: (err: PurchaseApiError) => {
          this.loading = false;
          this.toastr.error(err.message);
          void this.router.navigate(['/pocketbiz/purchases']);
        },
      });
  }
}
