import { DatePipe } from '@angular/common';
import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { AccountingApiError } from '../../models/accounting';
import { JOURNAL_REASON_MAX, JournalEntryDetail } from '../../models/journal';
import { JournalApiService } from '../../services/journal-api.service';

/** Fecha local de hoy en `YYYY-MM-DD` (propuesta inicial de la reversión). */
export function todayIso(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

/**
 * Reversión de un asiento confirmado: muestra lo que se invierte y exige fecha y motivo. Se cierra devolviendo el
 * asiento de reversión; los errores del servidor quedan dentro del diálogo sin perder lo escrito.
 */
@Component({
  selector: 'app-journal-reverse-dialog',
  templateUrl: './journal-reverse-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, DatePipe],
})
export class JournalReverseDialogComponent {
  readonly maxLength = JOURNAL_REASON_MAX;
  readonly form = inject(FormBuilder).nonNullable.group({ reversalDate: todayIso(), reason: '' });
  readonly activeModal = inject(NgbActiveModal);
  entry: JournalEntryDetail | null = null;
  saving = false;
  dateError = '';
  reasonError = '';
  errorMessage = '';

  private api = inject(JournalApiService);
  private destroyRef = inject(DestroyRef);

  init(entry: JournalEntryDetail): void {
    this.entry = entry;
  }

  get reason(): string {
    return this.form.controls.reason.value.trim();
  }

  get canSubmit(): boolean {
    return !this.saving && !!this.form.controls.reversalDate.value && this.reason.length > 0 && this.reason.length <= this.maxLength;
  }

  submit(): void {
    const entry = this.entry;
    if (!entry || !this.canSubmit) return;
    this.saving = true;
    this.dateError = '';
    this.reasonError = '';
    this.errorMessage = '';
    this.api
      .reverse(entry.id, this.form.controls.reversalDate.value, this.reason)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (reversal) => this.activeModal.close(reversal),
        error: (err: AccountingApiError) => {
          this.saving = false;
          this.dateError = err.fieldErrors['reversal_date']?.join(' ') ?? '';
          this.reasonError = err.fieldErrors['reason']?.join(' ') ?? '';
          const other = Object.entries(err.fieldErrors)
            .filter(([field]) => field !== 'reversal_date' && field !== 'reason')
            .flatMap(([, messages]) => messages ?? []);
          this.errorMessage = this.dateError || this.reasonError ? other.join(' ') : other.join(' ') || err.message;
        },
      });
  }
}
