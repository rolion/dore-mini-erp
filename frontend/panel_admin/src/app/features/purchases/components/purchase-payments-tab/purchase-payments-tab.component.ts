import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject, input, output } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { PAYMENT_METHOD_LABELS, Payment, PaymentApiError } from '../../models/payment';
import { PAYMENT_STATUS_CLASSES, PAYMENT_STATUS_LABELS, Purchase } from '../../models/purchase';
import { PaymentsApiService } from '../../services/payments-api.service';
import { PaymentDialogComponent } from '../payment-dialog/payment-dialog.component';

/** Pestaña «Pagos» de la compra: resumen de saldo, tabla de pagos y alta mediante diálogo. */
@Component({
  selector: 'app-purchase-payments-tab',
  templateUrl: './purchase-payments-tab.component.html',
  imports: [TranslatePipe, DatePipe, MoneyPipe],
})
export class PurchasePaymentsTabComponent implements OnInit {
  readonly purchase = input.required<Purchase>();
  /** Se emite tras registrar un pago, para que el detalle relea la compra (saldo, estado y acciones). */
  readonly paid = output<void>();
  readonly statusLabels = PAYMENT_STATUS_LABELS;
  readonly statusClasses = PAYMENT_STATUS_CLASSES;
  readonly methodLabels = PAYMENT_METHOD_LABELS;
  payments: Payment[] = [];
  loading = true;
  errorMessage = '';

  private api = inject(PaymentsApiService);
  private modal = inject(NgbModal);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.load();
  }

  get isConfirmed(): boolean {
    return this.purchase().status === 'confirmed';
  }

  get canPay(): boolean {
    return this.purchase().allowedActions.includes('pay');
  }

  /** Por qué no se puede pagar (vacío si se puede o si no hace falta explicarlo). */
  get blockedReason(): string {
    const p = this.purchase();
    if (this.canPay) return '';
    if (p.status === 'draft') return tr('PURCHASES.PURCHASE_PAYMENTS_TAB.CONFIRMA_LA_COMPRA_PARA_REGISTRAR');
    if (p.status === 'cancelled') return tr('PURCHASES.PURCHASE_PAYMENTS_TAB.LA_COMPRA_ESTA_CANCELADA');
    if (p.paymentStatus === 'paid') return tr('CUSTOMERS.CUSTOMER_PURCHASE_HISTORY.PAGADO');
    return tr('PURCHASES.PURCHASE_PAYMENTS_TAB.SIN_SALDO_POR_PAGAR');
  }

  load(): void {
    this.loading = true;
    this.errorMessage = '';
    this.api
      .list(this.purchase().id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (page) => {
          this.payments = page.results;
          this.loading = false;
        },
        error: (err: PaymentApiError) => {
          this.errorMessage = err.message;
          this.loading = false;
        },
      });
  }

  async register(): Promise<void> {
    const ref = this.modal.open(PaymentDialogComponent, { backdrop: 'static' });
    const dialog = ref.componentInstance as PaymentDialogComponent;
    dialog.init(this.purchase());
    // Un rechazo por saldo desactualizado relee la compra: se refresca el fondo mientras el diálogo sigue abierto.
    dialog.purchaseRefreshed.subscribe(() => {
      this.load();
      this.paid.emit();
    });
    try {
      await ref.result;
    } catch {
      return; // «Cancelar»: no cambia nada.
    }
    this.toastr.success(tr('PURCHASES.PURCHASE_PAYMENTS_TAB.PAGO_REGISTRADO'));
    this.load();
    this.paid.emit();
  }
}
