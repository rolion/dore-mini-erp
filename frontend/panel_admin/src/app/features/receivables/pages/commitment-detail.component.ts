import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, ViewChild, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize } from 'rxjs';
import { PaymentDialogComponent } from '../../../shared/components/payment-dialog/payment-dialog.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import {
  CollectionPayment, Commitment, PAYMENT_TONES, PaymentRegistered, ReceivableFailure, SourceKind, methodLabel, statusLabel,
} from '../../../shared/models/receivable';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { ReceivablesApiService } from '../../../shared/services/receivables-api.service';

/**
 * Cobro de una proforma: propuesto/aceptado/cobrado/saldo, tratamientos y pagos. El pago se registra con el diálogo
 * compartido (el mismo que se abre desde la proforma y la ficha del paciente).
 */
@Component({
  selector: 'app-commitment-detail',
  imports: [RouterLink, MoneyPipe, DatePipe, TranslatePipe, PaymentDialogComponent, StatusBadgeComponent],
  templateUrl: './commitment-detail.component.html',
})
export class CommitmentDetailComponent implements OnInit {
  private api = inject(ReceivablesApiService);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);

  @ViewChild(PaymentDialogComponent) private payment?: PaymentDialogComponent;

  readonly statusLabel = statusLabel;
  readonly methodLabel = methodLabel;
  readonly tones = PAYMENT_TONES;

  kind: SourceKind = 'quotation';
  number = '';
  commitment: Commitment | null = null;
  loading = true;
  error = '';
  receipt: PaymentRegistered | null = null;

  ngOnInit(): void {
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      this.kind = params.get('kind') === 'dental' ? 'dental' : 'quotation';
      this.number = params.get('number') ?? '';
      this.load();
    });
  }

  get canPay(): boolean {
    return !!this.commitment?.allowed_actions.includes('register_payment');
  }

  /** Ruta de la proforma de origen (usa el id de la versión vigente que informa el servidor). */
  get proformaLink(): string[] {
    const base = this.kind === 'dental' ? '/pocketbiz/dentistry/proformas' : '/pocketbiz/quotations/proformas';
    const id = this.commitment?.proforma_id;
    return id ? [base, id] : [base];
  }

  get patientLink(): string[] | null {
    return this.kind === 'dental' && this.commitment ? ['/pocketbiz/dentistry/patients', this.commitment.customer_id] : null;
  }

  load(): void {
    this.loading = true;
    this.error = '';
    this.api
      .get(this.kind, this.number)
      .pipe(takeUntilDestroyed(this.destroyRef), finalize(() => (this.loading = false)))
      .subscribe({
        next: (commitment) => (this.commitment = commitment),
        error: (failure: ReceivableFailure) => (this.error = failure.message),
      });
  }

  openPayment(opener: EventTarget | null): void {
    this.receipt = null;
    this.payment?.open(opener instanceof HTMLElement ? opener : null);
  }

  onPaid(result: PaymentRegistered): void {
    this.receipt = result;
    this.load();
  }

  methodOf(payment: CollectionPayment): string {
    return methodLabel(payment.payment_method);
  }
}
