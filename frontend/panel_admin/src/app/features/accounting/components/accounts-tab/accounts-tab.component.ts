import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Subject, catchError, finalize, switchMap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { Account, AccountingApiError } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';
import { AccountDialogComponent } from '../account-dialog/account-dialog.component';
import { DeactivateDialogComponent } from '../deactivate-dialog/deactivate-dialog.component';

export type StatusFilter = 'all' | 'active' | 'inactive';

/** Pestaña «Cuentas»: listado con filtro de estado (inicialmente activas) y alta/edición en diálogo. */
@Component({
  selector: 'app-accounts-tab',
  templateUrl: './accounts-tab.component.html',
  styleUrl: './accounts-tab.component.scss',
  imports: [TranslatePipe, ReactiveFormsModule],
})
export class AccountsTabComponent implements OnInit {
  readonly statusControl = new FormControl<StatusFilter>('active', { nonNullable: true });

  rows: Account[] = [];
  loading = false;
  errorMessage = '';
  /** Motivo de un bloqueo del servidor (la cuenta la usan métodos activos), visible sobre la tabla. */
  blockReason = '';

  private api = inject(AccountingApiService);
  private modal = inject(NgbModal);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  ngOnInit(): void {
    this.reload$
      .pipe(
        switchMap(() => {
          this.loading = true;
          this.errorMessage = '';
          return this.api.listAccounts(this.activeFilter()).pipe(
            catchError((err: AccountingApiError) => {
              this.errorMessage = err.message;
              this.rows = [];
              return EMPTY;
            }),
            finalize(() => (this.loading = false)),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((accounts) => (this.rows = accounts));
    this.statusControl.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.reload$.next());
    this.reload$.next();
  }

  reload(): void {
    this.reload$.next();
  }

  openDialog(account?: Account): void {
    this.blockReason = '';
    const ref = this.modal.open(AccountDialogComponent, { centered: true });
    const dialog = ref.componentInstance as AccountDialogComponent;
    if (account) {
      dialog.edit(account);
    }
    ref.result.then(
      () => this.reload$.next(),
      () => undefined, // cancelado: no hay nada que recargar
    );
  }

  /** Desactivar pide confirmación (con los métodos activos que la usan); activar es directo. */
  toggleActive(account: Account): void {
    this.blockReason = '';
    if (!account.isActive) {
      this.apply(this.api.activateAccount(account.id));
      return;
    }
    this.api
      .listMethods()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (methods) => this.confirmDeactivation(account, methods.filter((m) => m.isActive && m.account?.id === account.id).map((m) => m.label)),
        error: (err: AccountingApiError) => this.toastr.error(err.message),
      });
  }

  private confirmDeactivation(account: Account, usedBy: string[]): void {
    const ref = this.modal.open(DeactivateDialogComponent, { centered: true });
    const dialog = ref.componentInstance as DeactivateDialogComponent;
    dialog.account = account;
    dialog.methods = usedBy;
    ref.result.then(
      () => this.apply(this.api.deactivateAccount(account.id)),
      () => undefined, // cancelado
    );
  }

  private apply(request: ReturnType<AccountingApiService['activateAccount']>): void {
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.toastr.success(updated.isActive ? tr('ACCOUNTING.ACCOUNTS_TAB.CUENTA_ACTIVADA') : tr('ACCOUNTING.ACCOUNTS_TAB.CUENTA_DESACTIVADA'));
        this.reload$.next();
      },
      error: (err: AccountingApiError) => {
        if (err.status === 409) {
          this.blockReason = err.message;
        } else {
          this.toastr.error(err.message);
        }
      },
    });
  }

  private activeFilter(): boolean | undefined {
    switch (this.statusControl.value) {
      case 'active':
        return true;
      case 'inactive':
        return false;
      default:
        return undefined;
    }
  }
}
