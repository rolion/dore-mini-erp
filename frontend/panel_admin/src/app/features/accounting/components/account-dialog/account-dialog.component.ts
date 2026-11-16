import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { ToastrService } from 'ngx-toastr';
import { tr } from '../../../../core/i18n/translate';
import {
  ACCOUNT_CLASSES,
  ACCOUNT_CODE_MAX_LENGTH,
  ACCOUNT_CODE_PATTERN,
  ACCOUNT_KINDS,
  ACCOUNT_NAME_MAX_LENGTH,
  Account,
  AccountClassCode,
  AccountInput,
  AccountClassState,
  AccountKind,
  AccountingApiError,
  CURRENCIES,
} from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';

/** Longitud máxima del valor recortado (el servidor recorta antes de validar). */
function maxTrimmedLength(max: number): (control: AbstractControl<string>) => ValidationErrors | null {
  return (control) => (control.value.trim().length > max ? { maxlength: { requiredLength: max, actualLength: control.value.trim().length } } : null);
}

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

export type AccountField = 'name' | 'currency' | 'kind' | 'openingBalance' | 'accountClass' | 'code';

/** Decimal no negativo con hasta 2 decimales. */
export const OPENING_BALANCE_PATTERN = /^\d{1,10}(\.\d{1,2})?$/;

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
  readonly kinds = ACCOUNT_KINDS;
  readonly codeMaxLength = ACCOUNT_CODE_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group({
    code: ['', [notBlank, maxTrimmedLength(ACCOUNT_CODE_MAX_LENGTH), Validators.pattern(ACCOUNT_CODE_PATTERN)]],
    name: ['', [notBlank, Validators.maxLength(ACCOUNT_NAME_MAX_LENGTH)]],
    currency: ['BOB', Validators.required],
    accountClass: ['' as AccountClassCode | '', Validators.required],
    kind: ['' as AccountKind | ''],
    isContra: [false],
    openingBalance: ['0.00', [Validators.required, Validators.pattern(OPENING_BALANCE_PATTERN)]],
  });

  /** Estado de las seis clasificaciones en la empresa; vacío mientras carga o si falla (el selector queda sin opciones). */
  classStates: AccountClassState[] = [];

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
    this.api
      .listAccountClasses()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: (rows) => (this.classStates = rows), error: () => (this.classStates = []) });
    // El tipo de dinero solo existe en cuentas de Activo: al elegir otra clasificación se limpia.
    this.form.controls.accountClass.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((value) => {
      if (value !== 'ASSET') {
        this.form.controls.kind.setValue('', { emitEvent: false });
      }
    });
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.serverErrors = {};
      this.blockReason = '';
    });
  }

  /** Tipo de dinero a enviar: el elegido (solo Activo); `null` para quitarlo si la cuenta lo tenía; nada si no cambia. */
  private kindChange(accountClass: AccountClassCode | '', kind: AccountKind | ''): { kind?: AccountKind | null } {
    if (accountClass === 'ASSET' && kind !== '') {
      return { kind };
    }
    return this.account?.kind ? { kind: null } : {};
  }

  /** El tipo de cuenta de dinero solo se ofrece con clasificación Activo. */
  get showKind(): boolean {
    return this.form.controls.accountClass.value === 'ASSET';
  }

  get isEdit(): boolean {
    return this.account !== null;
  }

  /** Opciones del selector: solo las habilitadas, más la actual de la cuenta aunque esté deshabilitada. */
  get classOptions(): { code: AccountClassCode; disabled: boolean }[] {
    const current = this.account?.accountClass ?? null;
    const enabled = new Set(this.classStates.filter((s) => s.enabled).map((s) => s.code));
    return ACCOUNT_CLASSES.filter((code) => enabled.has(code) || code === current).map((code) => ({ code, disabled: !enabled.has(code) }));
  }

  edit(account: Account): void {
    this.account = account;
    // Con asientos, la clasificación ya asignada y la marca de correctora no cambian (el servidor también lo rechaza).
    // Una cuenta anterior con asientos y sin clasificación sí puede completarla: el servidor lo permite.
    if (account.hasEntries) {
      if (account.accountClass) {
        this.form.controls.accountClass.disable();
      }
      this.form.controls.isContra.disable();
    }
    this.form.setValue({
      code: account.code ?? '',
      name: account.name,
      currency: account.currency,
      accountClass: account.accountClass ?? '',
      kind: account.kind ?? '',
      isContra: account.isContra ?? false,
      openingBalance: account.openingBalance,
    });
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
    if (value.accountClass === '') {
      return;
    }
    const body: AccountInput = {
      code: value.code.trim(),
      name: value.name.trim(),
      currency: value.currency,
      accountClass: value.accountClass,
      isContra: value.isContra,
      openingBalance: value.openingBalance,
      ...this.kindChange(value.accountClass, value.kind),
    };
    this.saving = true;
    const request = this.account ? this.api.updateAccount(this.account.id, body) : this.api.createAccount(body);
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
        for (const field of ['code', 'name', 'currency', 'kind', 'openingBalance', 'accountClass'] as const) {
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
