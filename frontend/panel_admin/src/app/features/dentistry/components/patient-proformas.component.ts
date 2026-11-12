import { DatePipe } from '@angular/common';
import { ChangeDetectorRef, Component, DestroyRef, Input, OnChanges, OnInit, ViewChild, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TranslatePipe } from '@ngx-translate/core';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { tr } from '../../../core/i18n/translate';
import { ModulesService } from '../../../core/service/modules.service';
import { PaymentDialogComponent } from '../../../shared/components/payment-dialog/payment-dialog.component';
import { PaymentRegistered, fromCents, toCents } from '../../../shared/models/receivable';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { ReceivablesApiService } from '../../../shared/services/receivables-api.service';
import { DentalProformaSummary, PROFORMA_STATUS_CLASSES, proformaStatusLabel } from '../models/dental-proforma';
import { DentalProformasApiService } from '../services/dental-proformas-api.service';

/** Tarjeta «Proformas» de la ficha del paciente: todas sus proformas de Odontología con su estado. */
@Component({
  selector: 'app-patient-proformas',
  imports: [RouterLink, MoneyPipe, DatePipe, TranslatePipe, PaymentDialogComponent],
  templateUrl: './patient-proformas.component.html',
})
export class PatientProformasComponent implements OnInit, OnChanges {
  private api = inject(DentalProformasApiService);
  private modules = inject(ModulesService);
  private receivables = inject(ReceivablesApiService);
  private cdr = inject(ChangeDetectorRef);
  private destroyRef = inject(DestroyRef);

  @Input({ required: true }) patientId = '';
  @Input() active = true;

  readonly statusLabel = proformaStatusLabel;
  readonly classes = PROFORMA_STATUS_CLASSES;

  @ViewChild(PaymentDialogComponent) private payment?: PaymentDialogComponent;

  servicesEnabled = false;
  receivablesEnabled = false;
  /** Cobrado por número de proforma (solo con Cobros habilitado); sin obligación = 0.00. */
  private paidByNumber = new Map<string, string>();
  collectionsError = false;
  payNumber = '';
  receipt: PaymentRegistered | null = null;
  rows: DentalProformaSummary[] = [];
  count = 0;
  page = 1;
  loading = false;
  error = '';

  ngOnInit(): void {
    this.modules.enabledKeys$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(keys => {
      const enabled = !!keys && keys.has('services');
      const receivables = !!keys && keys.has('receivables');
      const receivablesChanged = receivables !== this.receivablesEnabled;
      this.receivablesEnabled = receivables;
      if (enabled && !this.servicesEnabled) this.load(1);
      else if (enabled && receivablesChanged) this.loadCollections();
      this.servicesEnabled = enabled;
    });
  }

  ngOnChanges(): void {
    if (this.servicesEnabled) this.load(1);
  }

  get pages(): number {
    return Math.max(1, Math.ceil(this.count / 10));
  }

  load(page: number): void {
    if (!this.patientId) return;
    this.page = page;
    this.loading = true;
    this.error = '';
    this.api.listForPatient(this.patientId, { page }).pipe(
      takeUntilDestroyed(this.destroyRef), finalize(() => this.loading = false),
    ).subscribe({
      next: result => { this.rows = result.results; this.count = result.count; this.loadCollections(); },
      error: () => this.error = tr('DENTISTRY.PROFORMAS.ERR_LISTA'),
    });
  }

  /** Cobrado por proforma: una sola lectura a Cobros por paciente; si falla, la tabla sigue y muestra «—». */
  private loadCollections(): void {
    this.collectionsError = false;
    if (!this.receivablesEnabled || !this.patientId) { this.paidByNumber = new Map(); return; }
    this.receivables.list({ customer_id: this.patientId, page_size: 100 }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: result => this.paidByNumber = new Map(result.results.filter(o => o.kind === 'dental').map(o => [o.number, o.paid])),
      error: () => { this.paidByNumber = new Map(); this.collectionsError = true; },
    });
  }

  /** Cobrado y saldo de una fila vigente (presentada); `null` si no aplica o no se pudo leer. */
  collection(row: DentalProformaSummary): { paid: string; balance: string } | null {
    if (!this.receivablesEnabled || this.collectionsError || row.status !== 'presented') return null;
    const paid = this.paidByNumber.get(row.number) ?? '0.00';
    const balance = Math.max((toCents(row.accepted_total) ?? 0) - (toCents(paid) ?? 0), 0);
    return { paid, balance: fromCents(balance) };
  }

  canCollect(row: DentalProformaSummary): boolean {
    return !!row.collectible && Number(this.collection(row)?.balance ?? '0') > 0;
  }

  collect(row: DentalProformaSummary, opener: EventTarget | null): void {
    this.payNumber = row.number;
    this.receipt = null;
    this.cdr.detectChanges(); // el diálogo toma `number` por input: debe estar actualizado antes de abrir
    this.payment?.open(opener instanceof HTMLElement ? opener : null);
  }

  onPaid(result: PaymentRegistered): void {
    this.receipt = result;
    this.load(this.page);
  }
}
