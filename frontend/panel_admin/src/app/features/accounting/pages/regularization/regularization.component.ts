import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormArray, FormBuilder, FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize, forkJoin } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { RegularizationConfirmDialogComponent } from '../../components/regularization-confirm-dialog/regularization-confirm-dialog.component';
import { Account, AccountingApiError, FLOW_CURRENCY, PaymentMethod } from '../../models/accounting';
import { formatAmount, originLabel } from '../../models/entry';
import {
  RegularizationError,
  RegularizationInput,
  RegularizationStatus,
  RegularizationSummary,
  RuleDraft,
  isRulePartial,
  reasonLabel,
  statusAmounts,
  statusCount,
  statusLabel,
  toRequest,
} from '../../models/regularization';
import { AccountingApiService } from '../../services/accounting-api.service';
import { RegularizationApiService } from '../../services/regularization-api.service';

type RuleForm = FormGroup<{
  method: FormControl<string>;
  accountId: FormControl<string>;
  from: FormControl<string>;
  to: FormControl<string>;
}>;

/**
 * Contabilidad › Regularizar pagos históricos: configurar el mapeo → previsualizar (no escribe) → aplicar con confirmación.
 * El mapeo es siempre explícito: ninguna cuenta se precarga ni se infiere; sin regla, el pago queda pendiente.
 */
@Component({
  selector: 'app-regularization',
  templateUrl: './regularization.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, RouterLink],
})
export class RegularizationComponent implements OnInit {
  readonly originLabel = originLabel;
  readonly statusLabel = statusLabel;
  readonly reasonLabel = reasonLabel;

  methods: PaymentMethod[] = [];
  accounts: Account[] = [];
  summary: RegularizationSummary | null = null;
  /** Huella del formulario al previsualizar: si cambia, hay que volver a previsualizar antes de aplicar. */
  previewKey = '';
  loadingSetup = false;
  previewing = false;
  applying = false;
  setupError = '';
  errors: string[] = [];
  applied = false;
  inProgress = false;

  private api = inject(AccountingApiService);
  private regularization = inject(RegularizationApiService);
  private modal = inject(NgbModal);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;

  readonly form = this.fb.group({
    dateFrom: this.fb.control(''),
    dateTo: this.fb.control(''),
    rules: this.fb.array<RuleForm>([]),
  });

  get rules(): FormArray<RuleForm> {
    return this.form.controls.rules;
  }

  ngOnInit(): void {
    this.loadingSetup = true;
    forkJoin([this.api.listMethods(), this.api.listAccounts(true)])
      .pipe(
        finalize(() => (this.loadingSetup = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: ([methods, accounts]) => {
          this.methods = methods;
          this.accounts = accounts.filter((a) => a.currency === FLOW_CURRENCY);
        },
        error: (err: AccountingApiError) => (this.setupError = err.message),
      });
  }

  addRule(): void {
    this.rules.push(this.fb.group({ method: '', accountId: '', from: '', to: '' }));
  }

  removeRule(index: number): void {
    this.rules.removeAt(index);
  }

  get input(): RegularizationInput {
    const value = this.form.getRawValue();
    return { dateFrom: value.dateFrom, dateTo: value.dateTo, rules: value.rules as RuleDraft[] };
  }

  /** Hay filas a medias: se avisa y no se previsualiza, para no descartarlas en silencio. */
  get incompleteRules(): boolean {
    return this.input.rules.some(isRulePartial);
  }

  get rangeInvalid(): boolean {
    const { dateFrom, dateTo } = this.input;
    return !!dateFrom && !!dateTo && dateFrom > dateTo;
  }

  /** El formulario cambió después de previsualizar: lo que se ve ya no es lo que se aplicaría. */
  get stale(): boolean {
    return this.summary !== null && !this.applied && JSON.stringify(toRequest(this.input)) !== this.previewKey;
  }

  get missingCount(): number {
    return this.summary ? statusCount(this.summary, 'missing') : 0;
  }

  get canApply(): boolean {
    return !!this.summary && !this.applied && this.missingCount > 0 && !this.stale && !this.applying && !this.previewing;
  }

  get empty(): boolean {
    return !!this.summary && this.summary.totalPayments === 0;
  }

  count(status: RegularizationStatus): number {
    return this.summary ? statusCount(this.summary, status) : 0;
  }

  amounts(status: RegularizationStatus): string {
    return this.summary ? statusAmounts(this.summary, status).map((a) => formatAmount(a.amount, a.currency)).join(' · ') : '';
  }

  absentLabel(name: string): string {
    return tr(`ACCOUNTING.REGULARIZATION.AUSENTE.${name.toUpperCase()}`);
  }

  get absentEntries(): { name: string; count: number }[] {
    return Object.entries(this.summary?.absentFields ?? {}).map(([name, count]) => ({ name, count }));
  }

  money = formatAmount;

  methodLabel(code: string): string {
    return this.methods.find((m) => m.code === code)?.label ?? code;
  }

  preview(): void {
    if (this.previewing || this.rangeInvalid || this.incompleteRules) {
      return;
    }
    const request = toRequest(this.input);
    this.previewing = true;
    this.errors = [];
    this.applied = false;
    // Un resumen anterior (p. ej. el de una aplicación) no puede quedar bajo el aviso «no se ha escrito nada».
    this.summary = null;
    this.regularization
      .preview(request)
      .pipe(
        finalize(() => (this.previewing = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (summary) => {
          this.summary = summary;
          this.previewKey = JSON.stringify(request);
        },
        error: (err: RegularizationError) => this.fail(err),
      });
  }

  confirmApply(): void {
    if (!this.canApply || !this.summary) {
      return;
    }
    const ref = this.modal.open(RegularizationConfirmDialogComponent, { centered: true, backdrop: 'static' });
    ref.componentInstance.count = this.missingCount;
    ref.componentInstance.amounts = this.amounts('missing');
    ref.result.then(
      (confirmed: boolean) => (confirmed ? this.apply() : undefined),
      () => undefined,
    );
  }

  private apply(): void {
    const request = toRequest(this.input);
    this.applying = true;
    this.errors = [];
    this.regularization
      .apply(request)
      .pipe(
        finalize(() => (this.applying = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (summary) => {
          this.summary = summary;
          this.applied = true;
        },
        error: (err: RegularizationError) => this.fail(err),
      });
  }

  get resultMessage(): string {
    return tr('ACCOUNTING.REGULARIZATION.RESULTADO', {
      created: this.count('created'),
      existing: this.count('existing'),
      failed: this.count('failed'),
    });
  }

  private fail(err: RegularizationError): void {
    this.errors = err.messages.length ? err.messages : [err.message];
    this.inProgress = err.code === 'regularization_in_progress';
  }
}
