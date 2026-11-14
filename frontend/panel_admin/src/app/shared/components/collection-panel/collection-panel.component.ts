import { Component, DestroyRef, OnChanges, OnInit, ViewChild, computed, inject, input, output, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TranslatePipe } from '@ngx-translate/core';
import { ModulesService } from '../../../core/service/modules.service';
import { PaymentRegistered, SourceKind } from '../../models/receivable';
import { MoneyPipe } from '../../pipes/money.pipe';
import { ReceivablesApiService } from '../../services/receivables-api.service';
import { PaymentDialogComponent } from '../payment-dialog/payment-dialog.component';

/**
 * Cobro en contexto de una proforma: carga el estado de cobro (si el módulo Cobros está habilitado y la proforma
 * está presentada), aloja el diálogo de pago y muestra el comprobante. El padre lo usa por referencia de plantilla:
 * `collection.canCollect()`, `collection.state()` y `collection.open()`.
 */
@Component({
  selector: 'app-collection-panel',
  imports: [TranslatePipe, MoneyPipe, PaymentDialogComponent],
  templateUrl: './collection-panel.component.html',
})
export class CollectionPanelComponent implements OnInit, OnChanges {
  private api = inject(ReceivablesApiService);
  private modules = inject(ModulesService);
  private destroyRef = inject(DestroyRef);

  readonly kind = input.required<SourceKind>();
  readonly number = input.required<string>();
  readonly status = input.required<string>();
  /** Cambia cuando se registran decisiones: dispara una nueva lectura del estado de cobro. */
  readonly acceptedTotal = input<string>('');
  readonly paid = output<PaymentRegistered>();

  @ViewChild(PaymentDialogComponent, { static: true }) private dialog!: PaymentDialogComponent;

  readonly enabled = signal(false);
  /** Importe cobrado y saldo; `null` si Cobros no está habilitado o no se pudo leer. */
  readonly state = signal<{ paid: string; balance: string } | null>(null);
  readonly receipt = signal<PaymentRegistered | null>(null);
  readonly canCollect = computed(() => this.enabled() && this.status() === 'presented'
    && !!this.state() && Number(this.state()?.balance ?? '0') > 0);

  ngOnInit(): void {
    this.modules.enabledKeys$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((keys) => {
      const enabled = !!keys && keys.has('receivables');
      const changed = enabled !== this.enabled();
      this.enabled.set(enabled);
      if (changed) this.refresh();
    });
  }

  ngOnChanges(): void {
    this.refresh();
  }

  open(opener?: EventTarget | null): void {
    this.receipt.set(null);
    this.dialog.open(opener instanceof HTMLElement ? opener : null);
  }

  refresh(): void {
    if (!this.enabled() || this.status() === 'draft' || !this.number()) {
      this.state.set(null);
      return;
    }
    this.api.get(this.kind(), this.number()).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (commitment) => this.state.set({ paid: commitment.totals.paid, balance: commitment.totals.balance }),
      error: () => this.state.set(null),
    });
  }

  onPaid(result: PaymentRegistered): void {
    this.receipt.set(result);
    this.state.set({ paid: result.totals.paid, balance: result.totals.balance });
    this.paid.emit(result);
  }
}
