import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize } from 'rxjs';
import { tr } from '../../../core/i18n/translate';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import {
  CollectionPayment, Commitment, CommitmentLine, PAYMENT_METHODS, PaymentMethod, REFERENCE_MAX_LENGTH,
  ReceivableFailure, SourceKind, STATUS_CLASSES, fromCents, methodLabel, statusLabel, toCents,
} from '../models/receivable';
import { ReceivablesApiService } from '../services/receivables-api.service';

type Step = 'closed' | 'form' | 'summary';

/** Cobro de una proforma: propuesto/aceptado/cobrado/saldo, pagos y registro de anticipos y abonos con resumen. */
@Component({
  selector: 'app-commitment-detail',
  imports: [ReactiveFormsModule, RouterLink, MoneyPipe, DatePipe, TranslatePipe],
  templateUrl: './commitment-detail.component.html',
})
export class CommitmentDetailComponent implements OnInit {
  private api = inject(ReceivablesApiService);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;

  readonly statusLabel = statusLabel;
  readonly methodLabel = methodLabel;
  readonly classes = STATUS_CLASSES;
  readonly methods = PAYMENT_METHODS;
  readonly referenceMax = REFERENCE_MAX_LENGTH;
  readonly today = new Date().toISOString().slice(0, 10);

  kind: SourceKind = 'quotation';
  number = '';
  commitment: Commitment | null = null;
  loading = true;
  saving = false;
  error = '';
  step: Step = 'closed';
  failure: ReceivableFailure | null = null;
  receipt: CollectionPayment | null = null;
  /** Se genera al abrir el formulario y se conserva en los reintentos: el servidor no duplica el pago. */
  private idempotencyKey = '';

  readonly form = this.fb.group({
    amount: ['', [Validators.required]],
    payment_method: ['CASH' as PaymentMethod, [Validators.required]],
    payment_date: [this.today, [Validators.required]],
    reference: ['', [Validators.maxLength(REFERENCE_MAX_LENGTH)]],
    allocations: this.fb.array([]) as FormArray,
  });

  ngOnInit(): void {
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      this.kind = params.get('kind') === 'dental' ? 'dental' : 'quotation';
      this.number = params.get('number') ?? '';
      this.load();
    });
  }

  get allocations(): FormArray {
    return this.form.controls.allocations;
  }

  get payableLines(): CommitmentLine[] {
    return (this.commitment?.lines ?? []).filter((line) => line.collectible);
  }

  get originLink(): string {
    return this.kind === 'dental' ? '/pocketbiz/dentistry/patients' : '/pocketbiz/quotations/proformas';
  }

  get originQuery(): Record<string, string> | null {
    return this.kind === 'dental' ? null : { customer: this.number };
  }

  get canPay(): boolean {
    return !!this.commitment?.allowed_actions.includes('register_payment');
  }

  get allocatedCents(): number {
    return this.allocations.controls.reduce((sum, group) => sum + (toCents(group.get('amount')?.value) ?? 0), 0);
  }

  get amountCents(): number | null {
    return toCents(this.form.controls.amount.value);
  }

  /** Mensaje de validación de la distribución, o vacío si el formulario puede pasar al resumen. */
  get distributionError(): string {
    const amount = this.amountCents;
    if (amount === null || amount <= 0) return tr('RECEIVABLES.E_AMOUNT');
    const lines = this.payableLines;
    for (let i = 0; i < this.allocations.length; i++) {
      const value = this.allocations.at(i).get('amount')?.value;
      const cents = value ? toCents(value) : 0;
      if (cents === null) return tr('RECEIVABLES.E_ALLOCATIONS');
      if (cents > (toCents(lines[i]?.balance) ?? 0)) return tr('RECEIVABLES.E_SUPERA_SALDO');
    }
    if (this.allocatedCents !== amount) return tr('RECEIVABLES.E_SUMA');
    return '';
  }

  get summaryRows(): { description: string; amount: string }[] {
    const lines = this.payableLines;
    return this.allocations.controls
      .map((group, i) => ({ description: lines[i]?.description ?? '', amount: String(group.get('amount')?.value ?? '') }))
      .filter((row) => (toCents(row.amount) ?? 0) > 0);
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

  open(): void {
    this.idempotencyKey = crypto.randomUUID();
    this.receipt = null;
    this.failure = null;
    this.allocations.clear();
    for (let i = 0; i < this.payableLines.length; i++) this.allocations.push(this.fb.group({ amount: [''] }));
    this.form.patchValue({ amount: '', payment_method: 'CASH', payment_date: this.today, reference: '' });
    this.step = 'form';
  }

  cancel(): void {
    this.step = 'closed';
    this.failure = null;
  }

  /** Ayuda: reparte el monto en orden entre los tratamientos con saldo (el usuario puede editar el resultado). */
  distributeInOrder(): void {
    let remaining = this.amountCents ?? 0;
    this.payableLines.forEach((line, i) => {
      const part = Math.min(remaining, toCents(line.balance) ?? 0);
      remaining -= part;
      this.allocations.at(i).patchValue({ amount: part > 0 ? fromCents(part) : '' });
    });
  }

  review(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid || this.distributionError) return;
    this.step = 'summary';
  }

  back(): void {
    this.step = 'form';
    this.failure = null;
  }

  confirm(): void {
    if (this.saving || this.distributionError) return;
    const raw = this.form.getRawValue();
    const lines = this.payableLines;
    this.saving = true;
    this.failure = null;
    this.api
      .pay(this.kind, this.number, {
        idempotency_key: this.idempotencyKey,
        amount: fromCents(this.amountCents ?? 0),
        payment_method: raw.payment_method,
        payment_date: raw.payment_date || null,
        reference: raw.reference.trim(),
        allocations: this.allocations.controls
          .map((group, i) => ({ line_id: lines[i].line_id, amount: String(group.get('amount')?.value ?? '') }))
          .filter((row) => (toCents(row.amount) ?? 0) > 0)
          .map((row) => ({ line_id: row.line_id, amount: fromCents(toCents(row.amount) ?? 0) })),
      })
      .pipe(takeUntilDestroyed(this.destroyRef), finalize(() => (this.saving = false)))
      .subscribe({
        next: (result) => {
          const { payment, ...commitment } = result;
          this.commitment = commitment as Commitment;
          this.receipt = payment;
          this.step = 'closed';
        },
        error: (failure: ReceivableFailure) => {
          // Los datos del formulario se conservan; si el servidor rechazó por saldo, se recarga el compromiso.
          this.failure = failure;
          this.step = 'form';
          if (failure.conflict) this.load();
        },
      });
  }

  methodOf(payment: CollectionPayment): string {
    return methodLabel(payment.payment_method);
  }
}
