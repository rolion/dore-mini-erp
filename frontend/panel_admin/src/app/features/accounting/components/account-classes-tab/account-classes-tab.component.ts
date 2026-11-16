import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TranslatePipe } from '@ngx-translate/core';
import { ToastrService } from 'ngx-toastr';
import { tr } from '../../../../core/i18n/translate';
import { AccountClassState, AccountingApiError } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';

/** Pestaña «Clasificaciones contables»: las seis fijas, solo se habilitan o deshabilitan (CONT-08). */
@Component({
  selector: 'app-account-classes-tab',
  templateUrl: './account-classes-tab.component.html',
  imports: [TranslatePipe],
})
export class AccountClassesTabComponent implements OnInit {
  rows: AccountClassState[] = [];
  loading = false;
  errorMessage = '';
  /** Código de la fila con una petición en curso: evita dobles clics. */
  busyCode: string | null = null;

  private api = inject(AccountingApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.errorMessage = '';
    this.api
      .listAccountClasses()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (rows) => {
          this.rows = rows;
          this.loading = false;
        },
        error: (err: AccountingApiError) => {
          this.rows = [];
          this.errorMessage = err.message;
          this.loading = false;
        },
      });
  }

  toggle(row: AccountClassState): void {
    if (this.busyCode) {
      return;
    }
    this.busyCode = row.code;
    this.api
      .setAccountClassEnabled(row.code, !row.enabled)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (updated) => {
          this.rows = this.rows.map((r) => (r.code === updated.code ? updated : r));
          this.busyCode = null;
          this.toastr.success(updated.enabled ? tr('ACCOUNTING.ACCOUNT_CLASSES.HABILITADA_OK') : tr('ACCOUNTING.ACCOUNT_CLASSES.DESHABILITADA_OK'));
        },
        error: (err: AccountingApiError) => {
          this.busyCode = null;
          this.toastr.error(err.message);
        },
      });
  }
}
