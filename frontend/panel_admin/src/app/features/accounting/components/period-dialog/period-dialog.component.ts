import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, ValidatorFn, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { ToastrService } from 'ngx-toastr';
import { tr } from '../../../../core/i18n/translate';
import { ACCOUNT_NAME_MAX_LENGTH, AccountingApiError } from '../../models/accounting';
import { FiscalPeriod } from '../../models/fiscal-period';
import { FiscalPeriodsApiService } from '../../services/fiscal-periods-api.service';

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

/** El fin no puede ser anterior al inicio (ISO `yyyy-MM-dd` se compara como texto). */
const endNotBeforeStart: ValidatorFn = (group) => {
  const start = group.get('startDate')?.value as string;
  const end = group.get('endDate')?.value as string;
  return start && end && end < start ? { endBeforeStart: true } : null;
};

export type PeriodField = 'name' | 'startDate' | 'endDate';

/** Alta y edición de un período fiscal en un diálogo; se cierra devolviendo el período guardado. */
@Component({
  selector: 'app-period-dialog',
  templateUrl: './period-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule],
})
export class PeriodDialogComponent {
  readonly nameMaxLength = ACCOUNT_NAME_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group(
    {
      name: ['', [notBlank, Validators.maxLength(ACCOUNT_NAME_MAX_LENGTH)]],
      startDate: ['', Validators.required],
      endDate: ['', Validators.required],
    },
    { validators: endNotBeforeStart },
  );

  /** Período que se edita; `null` para crear. */
  period: FiscalPeriod | null = null;
  saving = false;
  serverErrors: Partial<Record<PeriodField, string>> = {};
  /** Motivo de un bloqueo del servidor (409): superposición o asientos que quedarían fuera. */
  blockReason = '';

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(FiscalPeriodsApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.serverErrors = {};
      this.blockReason = '';
    });
  }

  get isEdit(): boolean {
    return this.period !== null;
  }

  edit(period: FiscalPeriod): void {
    this.period = period;
    this.form.setValue({ name: period.name, startDate: period.startDate, endDate: period.endDate });
  }

  hasError(field: PeriodField): boolean {
    const control = this.form.controls[field];
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverErrors[field];
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const input = { name: value.name.trim(), startDate: value.startDate, endDate: value.endDate };
    this.saving = true;
    const request = this.period ? this.api.update(this.period.id, input) : this.api.create(input);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (saved) => {
        this.saving = false;
        this.toastr.success(this.isEdit ? tr('ACCOUNTING.FISCAL_PERIODS.ACTUALIZADO') : tr('ACCOUNTING.FISCAL_PERIODS.CREADO'));
        this.activeModal.close(saved);
      },
      error: (err: AccountingApiError) => {
        this.saving = false;
        if (err.status === 409) {
          this.blockReason = err.message;
          return;
        }
        const errors: Partial<Record<PeriodField, string>> = {};
        for (const field of ['name', 'startDate', 'endDate'] as const) {
          const messages = err.fieldErrors[field];
          if (messages?.length) {
            errors[field] = messages.join(' ');
          }
        }
        this.serverErrors = errors;
        if (!Object.keys(errors).length) {
          this.toastr.error(err.message);
        }
      },
    });
  }
}
