import { Component, DestroyRef, ElementRef, ViewChild, inject, input, output } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize } from 'rxjs';
import { tr } from '../../../core/i18n/translate';
import {
  Commitment, CommitmentLine, PAYMENT_METHODS, PaymentMethod, PaymentRegistered, REFERENCE_MAX_LENGTH,
  ReceivableFailure, SourceKind, fromCents, localToday, methodLabel, toCents,
} from '../../models/receivable';
import { MoneyPipe } from '../../pipes/money.pipe';
import { ReceivablesApiService } from '../../services/receivables-api.service';
import { Allocation, autoAllocate, halfOf, totalCents } from '../../utils/payment-allocation';

type Shortcut = 'total' | 'half' | 'other';

/**
 * Cobro de una proforma en un solo paso: saldo, monto con atajos, reparto automático en orden (editable bajo
 * «Distribuir por tratamiento») y una única confirmación. Lo abren la proforma, la ficha del paciente y Cobros.
 * Presentacional: el servidor valida líneas aceptadas, saldos, idempotencia y módulos.
 */
@Component({
  selector: 'app-payment-dialog',
  imports: [ReactiveFormsModule, MoneyPipe, TranslatePipe],
  templateUrl: './payment-dialog.component.html',
  styleUrl: './payment-dialog.component.scss',
})
export class PaymentDialogComponent {
  private api = inject(ReceivablesApiService);
  private fb = inject(FormBuilder).nonNullable;
  private destroyRef = inject(DestroyRef);

  readonly kind = input.required<SourceKind>();
  readonly number = input.required<string>();
  /** Se emite tras registrar el pago (el padre refresca y muestra el comprobante). */
  readonly paid = output<PaymentRegistered>();

  @ViewChild('dlg', { static: true }) private dialog!: ElementRef<HTMLDialogElement>;
  @ViewChild('amountInput') private amountInput?: ElementRef<HTMLInputElement>;

  readonly methods = PAYMENT_METHODS;
  readonly methodLabel = methodLabel;
  readonly referenceMax = REFERENCE_MAX_LENGTH;
  readonly today = localToday();

  commitment: Commitment | null = null;
  loading = false;
  saving = false;
  loadError = '';
  failure: ReceivableFailure | null = null;
  manual = false;
  /** Se genera al abrir y se conserva en los reintentos: el servidor no duplica el pago. */
  private idempotencyKey = '';
  private opener: HTMLElement | null = null;

  readonly form = this.fb.group({
    amount: ['', [Validators.required]],
    payment_method: ['CASH' as PaymentMethod, [Validators.required]],
    payment_date: [this.today, [Validators.required]],
    reference: ['', [Validators.maxLength(REFERENCE_MAX_LENGTH)]],
    allocations: this.fb.array([]) as FormArray,
  });

  get allocations(): FormArray {
    return this.form.controls.allocations;
  }

  get payableLines(): CommitmentLine[] {
    return (this.commitment?.lines ?? []).filter((line) => line.collectible);
  }

  get balanceCents(): number {
    return totalCents(this.payableLines);
  }

  get balanceText(): string {
    return fromCents(this.balanceCents);
  }

  get amountCents(): number | null {
    return toCents(this.form.controls.amount.value);
  }

  get shortcut(): Shortcut {
    const cents = this.amountCents;
    if (cents !== null && cents === this.balanceCents && cents > 0) return 'total';
    if (cents !== null && cents === halfOf(this.balanceCents) && cents > 0) return 'half';
    return 'other';
  }

  /** Imputaciones efectivas: las manuales o el reparto automático del monto. */
  get effective(): Allocation[] {
    if (this.manual) {
      return this.payableLines
        .map((line, i) => ({ line_id: line.line_id, cents: toCents(this.allocations.at(i)?.get('amount')?.value) ?? 0 }))
        .filter((row) => row.cents > 0);
    }
    return autoAllocate(this.amountCents ?? 0, this.payableLines);
  }

  get appliedRows(): { description: string; amount: string }[] {
    const byId = new Map(this.payableLines.map((line) => [line.line_id, line.description]));
    return this.effective.map((row) => ({ description: byId.get(row.line_id) ?? '', amount: fromCents(row.cents) }));
  }

  /** Mensaje de validación (vacío si se puede confirmar). */
  get validationError(): string {
    const amount = this.amountCents;
    if (amount === null || amount <= 0) return tr('RECEIVABLES.E_AMOUNT');
    if (amount > this.balanceCents) return tr('RECEIVABLES.E_SUPERA_SALDO');
    if (this.manual) {
      const lines = this.payableLines;
      for (let i = 0; i < lines.length; i++) {
        const value = this.allocations.at(i)?.get('amount')?.value;
        const cents = value ? toCents(value) : 0;
        if (cents === null) return tr('RECEIVABLES.E_ALLOCATIONS');
        if (cents > (toCents(lines[i].balance) ?? 0)) return tr('RECEIVABLES.E_SUPERA_SALDO');
      }
      if (this.effective.reduce((sum, row) => sum + row.cents, 0) !== amount) return tr('RECEIVABLES.E_SUMA');
    }
    return '';
  }

  get canConfirm(): boolean {
    return !this.saving && !this.loading && !!this.commitment && !this.validationError && this.form.valid;
  }

  open(opener?: HTMLElement | null): void {
    this.opener = opener ?? (document.activeElement as HTMLElement | null);
    this.idempotencyKey = crypto.randomUUID();
    this.failure = null;
    this.manual = false;
    this.form.reset({ amount: '', payment_method: 'CASH', payment_date: localToday(), reference: '' });
    this.allocations.clear();
    this.commitment = null;
    this.dialog.nativeElement.showModal();
    this.load(() => this.setAmountCents(this.balanceCents));
  }

  setShortcut(which: Shortcut): void {
    if (which === 'total') this.setAmountCents(this.balanceCents);
    else if (which === 'half') this.setAmountCents(halfOf(this.balanceCents));
    else {
      this.form.controls.amount.setValue('');
      this.amountInput?.nativeElement.focus();
    }
  }

  toggleManual(): void {
    this.manual = !this.manual;
    if (this.manual) this.rebuildAllocations(this.effectiveByLine());
  }

  confirm(): void {
    if (!this.canConfirm) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    this.saving = true;
    this.failure = null;
    this.api
      .pay(this.kind(), this.number(), {
        idempotency_key: this.idempotencyKey,
        amount: fromCents(this.amountCents ?? 0),
        payment_method: raw.payment_method,
        payment_date: raw.payment_date || null,
        reference: raw.reference.trim(),
        allocations: this.effective.map((row) => ({ line_id: row.line_id, amount: fromCents(row.cents) })),
      })
      .pipe(takeUntilDestroyed(this.destroyRef), finalize(() => (this.saving = false)))
      .subscribe({
        next: (result) => {
          this.close();
          this.paid.emit(result);
        },
        error: (failure: ReceivableFailure) => {
          // Los datos se conservan; ante un conflicto se recarga el compromiso y se reconstruye la distribución.
          this.failure = failure;
          if (failure.conflict) this.load(() => this.rebuildAllocations(new Map()));
        },
      });
  }

  close(): void {
    if (this.saving) return;
    this.dialog.nativeElement.close();
    this.opener?.focus();
  }

  private load(afterLoad: () => void): void {
    this.loading = true;
    this.loadError = '';
    this.api
      .get(this.kind(), this.number())
      .pipe(takeUntilDestroyed(this.destroyRef), finalize(() => (this.loading = false)))
      .subscribe({
        next: (commitment) => {
          this.commitment = commitment;
          afterLoad();
          setTimeout(() => this.amountInput?.nativeElement.focus());
        },
        error: (failure: ReceivableFailure) => (this.loadError = failure.message),
      });
  }

  private setAmountCents(cents: number): void {
    this.form.controls.amount.setValue(cents > 0 ? fromCents(cents) : '');
    if (this.manual) this.rebuildAllocations(this.effectiveByLine());
  }

  private effectiveByLine(): Map<string, number> {
    return new Map(autoAllocate(this.amountCents ?? 0, this.payableLines).map((row) => [row.line_id, row.cents]));
  }

  /** Una fila por tratamiento cobrable actual, ligada por posición a `payableLines` (se reconstruye al recargar). */
  private rebuildAllocations(values: Map<string, number>): void {
    this.allocations.clear();
    for (const line of this.payableLines) {
      const cents = values.get(line.line_id) ?? 0;
      this.allocations.push(this.fb.group({ amount: [cents > 0 ? fromCents(cents) : ''] }));
    }
  }
}
