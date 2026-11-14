import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { ToastrService } from 'ngx-toastr';
import { tr } from '../../../../core/i18n/translate';
import { ACCOUNT_NAME_MAX_LENGTH, Account, AccountingApiError, CURRENCIES } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

export type AccountField = 'name' | 'currency';

/** Alta y edición de una cuenta destino en un diálogo; se cierra devolviendo la cuenta guardada. */
@Component({
  selector: 'app-account-dialog',
  templateUrl: './account-dialog.component.html',
  styleUrl: './account-dialog.component.scss',
  imports: [TranslatePipe, ReactiveFormsModule],
})
export class AccountDialogComponent {
  readonly nameMaxLength = ACCOUNT_NAME_MAX_LENGTH;
  readonly currencies = CURRENCIES;
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [notBlank, Validators.maxLength(ACCOUNT_NAME_MAX_LENGTH)]],
    currency: ['BOB', Validators.required],
  });

  /** Cuenta que se edita; `null` para crear. Lo fija quien abre el diálogo. */
  account: Account | null = null;
  saving = false;
  serverErrors: Partial<Record<AccountField, string>> = {};
  /** Motivo de un bloqueo del servidor (409): la cuenta la usan métodos activos. */
  blockReason = '';

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(AccountingApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.serverErrors = {};
      this.blockReason = '';
    });
  }

  get isEdit(): boolean {
    return this.account !== null;
  }

  edit(account: Account): void {
    this.account = account;
    this.form.setValue({ name: account.name, currency: account.currency });
  }

  hasError(field: AccountField): boolean {
    const control = this.form.controls[field];
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverErrors[field];
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const input = { name: value.name.trim(), currency: value.currency };
    this.saving = true;
    const request = this.account ? this.api.updateAccount(this.account.id, input) : this.api.createAccount(input);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (saved) => {
        this.saving = false;
        this.toastr.success(this.isEdit ? tr('ACCOUNTING.ACCOUNT_DIALOG.CUENTA_ACTUALIZADA') : tr('ACCOUNTING.ACCOUNT_DIALOG.CUENTA_CREADA'));
        this.activeModal.close(saved);
      },
      error: (err: AccountingApiError) => {
        this.saving = false;
        if (err.status === 409) {
          this.blockReason = err.message;
          return;
        }
        const errors: Partial<Record<AccountField, string>> = {};
        for (const field of ['name', 'currency'] as const) {
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
