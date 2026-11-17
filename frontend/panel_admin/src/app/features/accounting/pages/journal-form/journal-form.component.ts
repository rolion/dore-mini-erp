import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormArray, FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { HasUnsavedChanges } from '../../../../core/guard/unsaved-changes.guard';
import { Account, AccountingApiError } from '../../models/accounting';
import {
  DraftLine,
  JOURNAL_DESCRIPTION_MAX,
  JOURNAL_MEMO_MAX,
  JOURNAL_MIN_LINES,
  JournalDraft,
  draftBlockers,
  draftTotals,
  formatCents,
  lineProblem,
  toJournalBody,
} from '../../models/journal';
import { AccountingApiService } from '../../services/accounting-api.service';
import { JournalApiService } from '../../services/journal-api.service';
import { todayIso } from '../../components/journal-reverse-dialog/journal-reverse-dialog.component';

/** Contabilidad › Movimientos › Nuevo asiento: un solo paso con Total Debe, Total Haber y Diferencia calculados. */
@Component({
  selector: 'app-journal-form',
  templateUrl: './journal-form.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, RouterLink],
})
export class JournalFormComponent implements OnInit, HasUnsavedChanges {
  readonly descriptionMax = JOURNAL_DESCRIPTION_MAX;
  readonly memoMax = JOURNAL_MEMO_MAX;
  readonly minLines = JOURNAL_MIN_LINES;
  accounts: Account[] = [];
  loadingAccounts = true;
  accountsError = '';
  saving = false;
  saved = false;
  /** Se muestran los problemas de cada línea solo después del primer intento de confirmar. */
  attempted = false;
  serverErrors: Record<string, string[]> = {};
  errorMessage = '';

  private fb = inject(FormBuilder);
  readonly form = this.fb.nonNullable.group({
    accountingDate: todayIso(),
    description: '',
    lines: this.fb.array([this.newLine(), this.newLine()]),
  });

  private accountingApi = inject(AccountingApiService);
  private api = inject(JournalApiService);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);

  get lines(): FormArray {
    return this.form.controls.lines;
  }

  ngOnInit(): void {
    this.accountingApi.listAccounts(true).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (accounts) => {
        this.accounts = accounts.filter((account) => !!account.code && !!account.accountClass);
        this.loadingAccounts = false;
      },
      error: (err: AccountingApiError) => {
        this.accountsError = err.message;
        this.loadingAccounts = false;
      },
    });
  }

  private newLine() {
    return this.fb.nonNullable.group({ accountId: '', debit: '', credit: '' });
  }

  get draft(): JournalDraft {
    const raw = this.form.getRawValue();
    return { accountingDate: raw.accountingDate, description: raw.description, lines: raw.lines as DraftLine[] };
  }

  get totals(): { debit: string; credit: string; difference: string; balanced: boolean } {
    const totals = draftTotals(this.draft.lines);
    return {
      debit: formatCents(totals.debit),
      credit: formatCents(totals.credit),
      difference: formatCents(totals.difference),
      balanced: totals.difference === 0 && totals.debit > 0,
    };
  }

  get blockers(): string[] {
    return draftBlockers(this.draft);
  }

  get canSubmit(): boolean {
    return !this.saving && this.blockers.length === 0;
  }

  get canRemove(): boolean {
    return this.lines.length > this.minLines;
  }

  addLine(): void {
    this.lines.push(this.newLine());
    this.form.markAsDirty();
  }

  removeLine(index: number): void {
    if (!this.canRemove) return;
    this.lines.removeAt(index);
    this.form.markAsDirty();
  }

  /** Escribir en un lado vacía el otro: una línea tiene Debe o Haber, nunca ambos. */
  onAmountInput(index: number, side: 'debit' | 'credit'): void {
    const group = this.lines.at(index);
    if (group.get(side)?.value) {
      group.get(side === 'debit' ? 'credit' : 'debit')?.setValue('');
    }
  }

  problem(index: number): string {
    return this.attempted ? lineProblem(this.draft.lines[index]) : '';
  }

  serverLineError(index: number): string {
    return Object.entries(this.serverErrors)
      .filter(([field]) => field.startsWith(`lines[${index}]`))
      .flatMap(([, messages]) => messages)
      .join(' ');
  }

  get linesError(): string {
    return (this.serverErrors['lines'] ?? []).join(' ');
  }

  fieldError(field: string): string {
    return (this.serverErrors[field] ?? []).join(' ');
  }

  hasUnsavedChanges(): boolean {
    return this.form.dirty && !this.saved;
  }

  submit(): void {
    this.attempted = true;
    if (!this.canSubmit) return;
    this.saving = true;
    this.serverErrors = {};
    this.errorMessage = '';
    this.api.create(toJournalBody(this.draft)).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (entry) => {
        this.saved = true;
        void this.router.navigate(['/pocketbiz/accounting/journal', entry.id], { queryParams: { created: 1 } });
      },
      error: (err: AccountingApiError) => {
        this.saving = false;
        this.serverErrors = Object.fromEntries(Object.entries(err.fieldErrors).map(([field, messages]) => [field, messages ?? []]));
        this.errorMessage = Object.keys(this.serverErrors).length ? '' : err.message;
      },
    });
  }
}
