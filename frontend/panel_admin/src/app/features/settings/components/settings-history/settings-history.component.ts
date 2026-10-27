import { DatePipe } from '@angular/common';
import { Component, DestroyRef, Input, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { HISTORY_PAGE_SIZE, SettingChange, SettingOption, SettingsApiError } from '../../models/setting';
import { SettingsApiService } from '../../services/settings-api.service';

/** Pestaña «Historial de cambios»: quién cambió qué ajuste, cuándo y con qué valores (filtros por fecha y ajuste). */
@Component({
  selector: 'app-settings-history',
  templateUrl: './settings-history.component.html',
  styleUrl: './settings-history.component.scss',
  imports: [ReactiveFormsModule, DatePipe, NgbPagination],
})
export class SettingsHistoryComponent implements OnInit {
  /** Ámbito: clave del módulo o `modules` (activación general). */
  @Input({ required: true }) scope = '';

  readonly pageSize = HISTORY_PAGE_SIZE;
  readonly filters = inject(FormBuilder).nonNullable.group({ dateFrom: '', dateTo: '', setting: '' });

  rows: SettingChange[] = [];
  options: SettingOption[] = [];
  count = 0;
  page = 1;
  loading = false;
  errorMessage = '';

  private api = inject(SettingsApiService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.load();
  }

  apply(): void {
    this.page = 1;
    this.load();
  }

  clear(): void {
    this.filters.reset();
    this.apply();
  }

  goTo(page: number): void {
    this.page = page;
    this.load();
  }

  load(): void {
    this.loading = true;
    this.errorMessage = '';
    const { dateFrom, dateTo, setting } = this.filters.getRawValue();
    this.api
      .history(this.scope, { dateFrom, dateTo, setting, page: this.page })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.loading = false;
          this.rows = result.results;
          this.count = result.count;
          this.options = result.settings;
        },
        error: (err: SettingsApiError) => {
          this.loading = false;
          this.errorMessage = err.message;
        },
      });
  }
}
