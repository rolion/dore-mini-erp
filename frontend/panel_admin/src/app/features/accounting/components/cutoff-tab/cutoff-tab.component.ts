import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { ToastrService } from 'ngx-toastr';
import { tr } from '../../../../core/i18n/translate';
import { AccountingApiError, AccountingSettings } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';

/** Pestaña «Corte y cobertura»: fecha de corte (editable hasta que haya movimientos) y periodos sin cobertura. */
@Component({
  selector: 'app-cutoff-tab',
  templateUrl: './cutoff-tab.component.html',
  styleUrl: './cutoff-tab.component.scss',
  imports: [TranslatePipe, ReactiveFormsModule, DatePipe],
})
export class CutoffTabComponent implements OnInit {
  readonly cutoffControl = new FormControl('', { nonNullable: true, validators: [Validators.required] });

  settings: AccountingSettings | null = null;
  loading = false;
  saving = false;
  errorMessage = '';
  serverError = '';

  private api = inject(AccountingApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.load();
  }

  get enabled(): boolean {
    return !!this.settings?.cutoffDate;
  }

  load(): void {
    this.loading = true;
    this.errorMessage = '';
    this.api
      .getSettings()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (settings) => {
          this.loading = false;
          this.apply(settings);
        },
        error: (err: AccountingApiError) => {
          this.loading = false;
          this.errorMessage = err.message;
        },
      });
  }

  save(): void {
    if (this.cutoffControl.invalid || this.saving || this.settings?.locked) {
      this.cutoffControl.markAsTouched();
      return;
    }
    this.saving = true;
    this.serverError = '';
    this.api
      .updateCutoff(this.cutoffControl.value)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (settings) => {
          this.saving = false;
          this.apply(settings);
          this.toastr.success(tr('ACCOUNTING.CUTOFF.CORTE_ACTUALIZADO'));
        },
        error: (err: AccountingApiError) => {
          this.saving = false;
          this.serverError = err.fieldErrors['cutoffDate']?.join(' ') || err.message;
        },
      });
  }

  private apply(settings: AccountingSettings): void {
    this.settings = settings;
    this.cutoffControl.setValue(settings.cutoffDate ?? '', { emitEvent: false });
    if (settings.locked) {
      this.cutoffControl.disable({ emitEvent: false });
    } else {
      this.cutoffControl.enable({ emitEvent: false });
    }
  }
}
