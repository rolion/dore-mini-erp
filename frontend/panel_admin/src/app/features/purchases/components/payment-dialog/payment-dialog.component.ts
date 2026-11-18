import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { Component, DestroyRef, OnInit, inject, output } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { PostingIssuesAlertComponent } from '../../../../shared/components/posting-issues-alert/posting-issues-alert.component';
import { EMPTY, catchError, debounceTime, finalize, of, switchMap, tap } from 'rxjs';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import {
  PAYMENT_METHODS,
  PAYMENT_METHOD_LABELS,
  Payment,
  PaymentApiError,
  PaymentFieldErrors,
  PaymentMethod,
  PaymentPostingIssue,
  PaymentPreview,
} from '../../models/payment';
import { Purchase, todayIso } from '../../models/purchase';
import { amountError } from '../../services/payment-amounts';
import { PaymentsApiService } from '../../services/payments-api.service';
import { PurchasesApiService } from '../../services/purchases-api.service';

/**
 * Alta de un pago. El diálogo hace la llamada: si el servidor rechaza, se queda abierto con lo escrito y muestra el
 * error. `paymentId` se genera al abrir y se reutiliza en cada reintento (idempotencia). Se cierra devolviendo el pago.
 */
@Component({
  selector: 'app-payment-dialog',
  templateUrl: './payment-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, MoneyPipe, PostingIssuesAlertComponent],
})
export class PaymentDialogComponent implements OnInit {
  readonly methods = PAYMENT_METHODS;
  readonly methodLabels = PAYMENT_METHOD_LABELS;
  readonly today = todayIso();
  readonly form = inject(FormBuilder).nonNullable.group({
    paymentDate: [todayIso(), Validators.required],
    amount: '',
    paymentMethod: '' as PaymentMethod | '',
  });
  readonly activeModal = inject(NgbActiveModal);
  /** Compra a pagar; la fija quien abre el diálogo. */
  purchase: Purchase | null = null;
  submitting = false;
  /** Se muestra tras un intento fallido o tocado el campo. */
  touched = false;
  serverErrors: PaymentFieldErrors = {};
  generalError = '';
  errorCode: string | null = null;
  /** Faltantes de configuración contable (409 del alta o de la vista previa). */
  postingIssues: PaymentPostingIssue[] = [];
  /** Asiento previsto según monto, método y fecha; `null` mientras falte algún dato válido. */
  preview: PaymentPreview | null = null;
  previewLoading = false;
  /** El servidor no pudo calcular el asiento previsto (no impide registrar el pago). */
  previewError = false;

  private paymentId: string = crypto.randomUUID();
  /** Se emite cuando se relee la compra tras un rechazo (saldo desactualizado), para refrescar el fondo. */
  readonly purchaseRefreshed = output<Purchase>();

  private api = inject(PaymentsApiService);
  private purchasesApi = inject(PurchasesApiService);
  private destroyRef = inject(DestroyRef);

  init(purchase: Purchase): void {
    this.purchase = purchase;
  }

  ngOnInit(): void {
    // La vista previa se pide al servidor (reparto deuda/anticipo y cuentas) cuando monto, método y fecha son válidos.
    this.form.valueChanges
      .pipe(
        tap(() => {
          this.preview = null;
          this.previewError = false;
          this.previewLoading = this.canPreview;
        }),
        debounceTime(300),
        switchMap(() => {
          const method = this.form.controls.paymentMethod.value;
          if (!this.purchase || !this.canPreview || !method) {
            this.previewLoading = false;
            return EMPTY;
          }
          return this.api
            .preview(this.purchase.id, {
              amount: this.form.controls.amount.value.trim(),
              paymentMethod: method,
              paymentDate: this.form.controls.paymentDate.value,
            })
            .pipe(catchError(() => of('error' as const)));
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((result) => {
        this.previewLoading = false;
        this.previewError = result === 'error';
        this.preview = result === 'error' ? null : result;
      });
  }

  /** Faltantes de configuración a mostrar: los del rechazo del alta o, si no hay, los de la vista previa. */
  get shownIssues(): PaymentPostingIssue[] {
    return this.postingIssues.length ? this.postingIssues : (this.preview?.issues ?? []);
  }

  /** La vista previa ya conoce faltantes de configuración: el servidor rechazaría el pago. */
  get blockedByPreview(): boolean {
    return (this.preview?.issues.length ?? 0) > 0;
  }

  private get canPreview(): boolean {
    return !this.amountMessage && !this.dateMessage && !this.methodMessage;
  }

  get balance(): string {
    return this.purchase?.balance ?? '0.00';
  }

  get amountMessage(): string | null {
    return amountError(this.form.controls.amount.value, this.balance);
  }

  get dateMessage(): string | null {
    const date = this.form.controls.paymentDate.value;
    if (!date) return tr('INVENTORY.STOCK_OPENING.LA_FECHA_ES_OBLIGATORIA');
    return date > this.today ? tr('PURCHASES.PAYMENT_DIALOG.LA_FECHA_NO_PUEDE_SER') : null;
  }

  get methodMessage(): string | null {
    return this.form.controls.paymentMethod.value ? null : tr('PURCHASES.PAYMENT_DIALOG.ELIGE_UN_METODO_DE_PAGO');
  }

  get canSubmit(): boolean {
    return !this.submitting && !this.amountMessage && !this.dateMessage && !this.methodMessage;
  }

  /** Mensajes visibles por campo (los del servidor tienen prioridad); vacíos hasta que se intenta enviar o se toca. */
  get dateError(): string | null {
    return this.touched ? (this.serverErrors.paymentDate ?? this.dateMessage) : null;
  }

  get amountFieldError(): string | null {
    return this.touched ? (this.serverErrors.amount ?? this.amountMessage) : null;
  }

  get methodError(): string | null {
    return this.touched ? (this.serverErrors.paymentMethod ?? this.methodMessage) : null;
  }

  private refreshPurchase(): void {
    const id = this.purchase?.id;
    if (!id) return;
    this.purchasesApi
      .get(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (fresh) => {
          this.purchase = fresh;
          this.purchaseRefreshed.emit(fresh);
        },
        error: () => undefined,
      });
  }

  /** Rellena el monto con todo el saldo. */
  payInFull(): void {
    this.form.controls.amount.setValue(this.balance);
    this.touched = true;
  }

  submit(): void {
    this.touched = true;
    const method = this.form.controls.paymentMethod.value;
    if (!this.purchase || !this.canSubmit || !method) return;
    this.submitting = true;
    this.serverErrors = {};
    this.generalError = '';
    this.errorCode = null;
    this.postingIssues = [];
    this.api
      .create(this.purchase.id, {
        paymentId: this.paymentId,
        amount: this.form.controls.amount.value.trim(),
        paymentMethod: method,
        paymentDate: this.form.controls.paymentDate.value,
      })
      .pipe(
        finalize(() => (this.submitting = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (payment: Payment) => this.activeModal.close(payment),
        error: (err: PaymentApiError) => {
          this.serverErrors = err.fieldErrors;
          this.errorCode = err.code;
          this.postingIssues = err.postingIssues;
          const hasField = !!(err.fieldErrors.amount || err.fieldErrors.paymentMethod || err.fieldErrors.paymentDate);
          this.generalError = hasField || err.postingIssues.length ? '' : err.message;
          // El saldo pudo cambiar en otra parte: se relee la compra para mostrar el vigente, sin tocar lo escrito.
          if (err.status === 400 || err.status === 409) this.refreshPurchase();
        },
      });
  }
}
