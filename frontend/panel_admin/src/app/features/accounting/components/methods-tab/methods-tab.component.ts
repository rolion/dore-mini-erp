import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { ToastrService } from 'ngx-toastr';
import { finalize, forkJoin } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { Account, AccountingApiError, FLOW_CURRENCY, PaymentMethod } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';

type MethodForm = FormGroup<{ accountId: FormControl<string>; isActive: FormControl<boolean> }>;

export interface MethodRow {
  method: PaymentMethod;
  form: MethodForm;
  saving: boolean;
  error: string;
}

/** Pestaña «Métodos de pago»: una fila fija por método con su cuenta destino y su estado (guardado por fila). */
@Component({
  selector: 'app-methods-tab',
  templateUrl: './methods-tab.component.html',
  styleUrl: './methods-tab.component.scss',
  imports: [TranslatePipe, ReactiveFormsModule],
})
export class MethodsTabComponent implements OnInit {
  rows: MethodRow[] = [];
  accounts: Account[] = [];
  loading = false;
  errorMessage = '';

  private api = inject(AccountingApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.errorMessage = '';
    forkJoin({ methods: this.api.listMethods(), accounts: this.api.listAccounts() })
      .pipe(
        finalize(() => (this.loading = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: ({ methods, accounts }) => {
          this.accounts = accounts;
          this.rows = methods.map((method) => this.toRow(method));
        },
        error: (err: AccountingApiError) => {
          this.errorMessage = err.message;
          this.rows = [];
        },
      });
  }

  /** Cuentas activas en la moneda de los flujos, más la cuenta actual del método aunque ya no sea elegible. */
  options(row: MethodRow): Account[] {
    const current = row.method.account;
    return this.accounts.filter((a) => (a.isActive && a.currency === FLOW_CURRENCY) || a.id === current?.id);
  }

  save(row: MethodRow): void {
    if (row.saving) {
      return;
    }
    const { accountId, isActive } = row.form.getRawValue();
    row.saving = true;
    row.error = '';
    this.api
      .configureMethod(row.method.code, accountId || null, isActive)
      .pipe(
        finalize(() => (row.saving = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (saved) => {
          row.method = saved;
          row.form.reset({ accountId: saved.account?.id ?? '', isActive: saved.isActive });
          this.toastr.success(tr('ACCOUNTING.METHODS_TAB.METODO_ACTUALIZADO'));
        },
        error: (err: AccountingApiError) => {
          const field = err.fieldErrors['accountId']?.join(' ');
          row.error = field || err.message;
        },
      });
  }

  private toRow(method: PaymentMethod): MethodRow {
    const form: MethodForm = this.fb.group({
      accountId: [method.account?.id ?? ''],
      isActive: [method.isActive],
    });
    return { method, form, saving: false, error: '' };
  }
}
