import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormArray, FormBuilder, FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { HasUnsavedChanges } from '../../../../core/guard/unsaved-changes.guard';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import {
  Adoption,
  DEFAULT_SOURCE,
  METHOD_LABEL,
  PENDING_LABEL,
  Proposal,
  ProposalBlocker,
  ProposalLine,
  SOURCE_MAX_LENGTH,
  lineValueMessage,
  lineValueState,
  previewUnitCost,
} from '../../models/valuation';
import { formatQuantity, newUuid } from '../../models/stock';
import { ValuationApiError, ValuationApiService, ValuationLineErrors } from '../../services/valuation-api.service';

export type ValuationPhase = 'loading' | 'error' | 'adopted' | 'wizard';
export type ValuationStep = 'reconcile' | 'values' | 'review';

export const ADOPTION_SUCCESS_MESSAGE = 'Valoración adoptada';
export const STOCK_CHANGED_MESSAGE = 'Las existencias cambiaron desde la conciliación. Revisa las cantidades y vuelve a ingresar los valores que falten.';

type RowGroup = FormGroup<{
  totalValue: FormControl<string>;
  declaredZero: FormControl<boolean>;
  source: FormControl<string>;
}>;

export interface ReviewRow {
  productName: string;
  quantity: string;
  unit: string;
  totalValue: string;
  unitCost: string;
  declaredZero: boolean;
  source: string;
}

/** Inventario › Valoración: asistente Conciliar → Valores → Confirmar, y consulta del corte adoptado. */
@Component({
  selector: 'app-valuation',
  templateUrl: './valuation.component.html',
  styleUrl: './valuation.component.scss',
  imports: [ReactiveFormsModule, RouterLink, DatePipe, MoneyPipe],
})
export class ValuationComponent implements OnInit, HasUnsavedChanges {
  readonly pendingLabel = PENDING_LABEL;
  readonly methodLabel = METHOD_LABEL;
  readonly sourceMaxLength = SOURCE_MAX_LENGTH;
  readonly defaultSource = DEFAULT_SOURCE;
  private readonly fb = inject(FormBuilder).nonNullable;
  private readonly api = inject(ValuationApiService);
  private readonly toastr = inject(ToastrService);
  private readonly destroyRef = inject(DestroyRef);

  phase: ValuationPhase = 'loading';
  step: ValuationStep = 'reconcile';
  errorMessage = '';
  proposal: Proposal = { lines: [], blockers: [] };
  adoption: Adoption | null = null;
  search = '';
  saving = false;
  /** Rechazo de regla del servidor (409) o error general al confirmar. */
  conflictMessage = '';
  serverBlockers: ProposalBlocker[] = [];
  serverLineErrors: ValuationLineErrors[] = [];
  readonly rows: FormArray<RowGroup> = this.fb.array<RowGroup>([]);
  readonly rowsForm = this.fb.group({ rows: this.rows });

  /** Clave de idempotencia: se genera al abrir la pantalla y se reenvía en cada intento de confirmación. */
  private readonly adoptionId = newUuid();

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.phase = 'loading';
    this.api
      .get()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (valuation) => {
          if (valuation.adoption) {
            this.adoption = valuation.adoption;
            this.phase = 'adopted';
          } else {
            this.loadProposal('reconcile');
          }
        },
        error: (err: ValuationApiError) => this.fail(err),
      });
  }

  private loadProposal(step: ValuationStep, message = ''): void {
    this.api
      .proposal()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (proposal) => {
          const previousLines = this.proposal.lines;
          this.proposal = proposal;
          this.rebuildRows(previousLines, proposal.lines);
          this.step = step;
          this.conflictMessage = message;
          this.serverBlockers = [];
          this.phase = 'wizard';
        },
        error: (err: ValuationApiError) => this.fail(err),
      });
  }

  private rebuildRows(previousLines: ProposalLine[], lines: ProposalLine[]): void {
    const previous = new Map<string, { totalValue: string; declaredZero: boolean; source: string }>();
    previousLines.forEach((line, index) => {
      const row = this.rows.at(index)?.getRawValue();
      if (row) {
        previous.set(line.productId, row);
      }
    });
    this.rows.clear();
    this.serverLineErrors = [];
    for (const line of lines) {
      const kept = previous.get(line.productId);
      this.rows.push(
        this.fb.group({
          totalValue: [kept?.totalValue ?? ''],
          declaredZero: [kept?.declaredZero ?? false],
          source: [kept?.source ?? ''],
        }),
      );
    }
  }

  private fail(err: ValuationApiError): void {
    this.errorMessage = err.message;
    this.phase = 'error';
  }

  // --- Conciliar -----------------------------------------------------------------------------------------------

  get blockers(): ProposalBlocker[] {
    return this.serverBlockers.length ? this.serverBlockers : this.proposal.blockers;
  }

  get canContinue(): boolean {
    return this.blockers.length === 0;
  }

  quantity(line: ProposalLine): string {
    return formatQuantity(line.reconciledQuantity);
  }

  amount(value: string): string {
    return formatQuantity(value);
  }

  goToValues(): void {
    if (this.canContinue) {
      this.step = 'values';
    }
  }

  reconcileAgain(): void {
    this.conflictMessage = '';
    this.loadProposal('reconcile');
  }

  // --- Valores -------------------------------------------------------------------------------------------------

  private rowValue(index: number) {
    return this.rows.at(index).getRawValue();
  }

  rowState(index: number) {
    const { totalValue, declaredZero } = this.rowValue(index);
    return lineValueState(totalValue, declaredZero);
  }

  isPending(index: number): boolean {
    return this.rowState(index) === 'pending';
  }

  /** Mensaje del servidor de la línea si lo hay; si no, el de la captura local (solo tras tocar el campo). */
  rowMessage(index: number): string | null {
    const server = this.serverLineErrors[index]?.totalValue?.[0];
    if (server) {
      return server;
    }
    const control = this.rows.at(index).controls.totalValue;
    const declaredZero = this.rows.at(index).controls.declaredZero.value;
    if (!(control.dirty || declaredZero)) {
      return null;
    }
    const state = this.rowState(index);
    return state === 'pending' ? null : lineValueMessage(state);
  }

  sourceMessage(index: number): string | null {
    return this.serverLineErrors[index]?.source?.[0] ?? null;
  }

  unitCost(index: number): string | null {
    const { totalValue, declaredZero } = this.rowValue(index);
    return previewUnitCost(totalValue, declaredZero, this.proposal.lines[index].reconciledQuantity);
  }

  onValueEdited(index: number): void {
    if (this.serverLineErrors[index]) {
      this.serverLineErrors = this.serverLineErrors.map((errors, i) => (i === index ? {} : errors));
    }
  }

  onZeroToggled(index: number): void {
    const row = this.rows.at(index);
    if (row.controls.declaredZero.value) {
      row.controls.totalValue.setValue('');
    }
    this.onValueEdited(index);
  }

  get pendingCount(): number {
    return this.rows.controls.filter((_, index) => this.rowState(index) === 'pending').length;
  }

  get canReview(): boolean {
    return this.rows.controls.every((_, index) => this.rowState(index) === 'ok');
  }

  backToReconcile(): void {
    this.step = 'reconcile';
  }

  review(): void {
    if (this.canReview) {
      this.conflictMessage = '';
      this.step = 'review';
    }
  }

  // --- Confirmar -----------------------------------------------------------------------------------------------

  get reviewRows(): ReviewRow[] {
    return this.proposal.lines.map((line, index) => {
      const row = this.rowValue(index);
      return {
        productName: line.productName,
        quantity: this.quantity(line),
        unit: line.unitAbbreviation ?? '',
        totalValue: row.declaredZero ? '0.00' : row.totalValue.trim(),
        unitCost: this.unitCost(index) ?? '',
        declaredZero: row.declaredZero,
        source: row.source.trim() || DEFAULT_SOURCE,
      };
    });
  }

  get totalValue(): string {
    const cents = this.reviewRows.reduce((sum, row) => sum + this.toCents(row.totalValue), BigInt(0));
    const digits = cents.toString().padStart(3, '0');
    return `${digits.slice(0, -2)}.${digits.slice(-2)}`;
  }

  private toCents(value: string): bigint {
    const [whole, fraction = ''] = value.split('.');
    return BigInt(whole + fraction.padEnd(2, '0'));
  }

  backToValues(): void {
    this.step = 'values';
  }

  confirm(): void {
    if (this.saving || !this.canReview) {
      return;
    }
    this.saving = true;
    this.conflictMessage = '';
    this.api
      .adopt({
        adoptionId: this.adoptionId,
        lines: this.proposal.lines.map((line, index) => {
          const row = this.rowValue(index);
          return {
            productId: line.productId,
            reconciledQuantity: line.reconciledQuantity,
            totalValue: row.declaredZero ? '' : row.totalValue,
            declaredZero: row.declaredZero,
            source: row.source,
          };
        }),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (adoption) => {
          this.saving = false;
          this.rows.markAsPristine();
          this.adoption = adoption;
          this.phase = 'adopted';
          this.toastr.success(ADOPTION_SUCCESS_MESSAGE);
        },
        error: (err: ValuationApiError) => {
          this.saving = false;
          this.onConfirmError(err);
        },
      });
  }

  private onConfirmError(err: ValuationApiError): void {
    if (err.status === 400) {
      this.serverLineErrors = err.lineErrors;
      this.conflictMessage = err.message;
      this.step = 'values';
    } else if (err.code === 'negative_stock') {
      this.serverBlockers = err.blockers;
      this.conflictMessage = err.message;
      this.step = 'reconcile';
    } else if (err.code === 'stock_changed') {
      this.loadProposal('reconcile', STOCK_CHANGED_MESSAGE);
    } else if (err.code === 'valuation_already_adopted' || err.code === 'adoption_id_reused') {
      this.conflictMessage = err.message;
      this.load();
    } else {
      this.conflictMessage = err.message;
    }
  }

  // --- Consulta ------------------------------------------------------------------------------------------------

  get filteredLines() {
    const text = this.search.trim().toLowerCase();
    const lines = this.adoption?.lines ?? [];
    return text ? lines.filter((line) => line.productName.toLowerCase().includes(text)) : lines;
  }

  onSearch(event: Event): void {
    this.search = (event.target as HTMLInputElement).value;
  }

  hasUnsavedChanges(): boolean {
    return this.phase === 'wizard' && this.rows.dirty;
  }
}
