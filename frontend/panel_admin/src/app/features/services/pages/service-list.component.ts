import { tr } from '../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, finalize, startWith, switchMap, throwError } from 'rxjs';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { SpecialtyOption } from '../../personnel/models/profile';
import { PersonnelApiService } from '../../personnel/services/personnel-api.service';
import { ServiceToggleComponent } from '../components/service-toggle.component';
import { CatalogService, ServiceApiError } from '../models/service';
import { ServiceFiltersState, ServicesApiService } from '../services/services-api.service';

@Component({ selector: 'app-service-list',
  imports: [TranslatePipe, ReactiveFormsModule, RouterLink, NgxDatatableModule, MoneyPipe, ServiceToggleComponent],
  templateUrl: './service-list.component.html',
  styleUrl: './service-list.component.scss',
})
export class ServiceListComponent implements OnInit {
  readonly state = inject(ServiceFiltersState);
  private api = inject(ServicesApiService);
  private personnel = inject(PersonnelApiService);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();
  search = new FormControl(this.state.search, { nonNullable: true });
  status = new FormControl(this.state.status, { nonNullable: true });
  specialty = new FormControl({ value: this.state.specialtyId, disabled: true }, { nonNullable: true });
  specialties: SpecialtyOption[] = [];
  specialtiesAvailable = false;
  rows: CatalogService[] = [];
  total = 0;
  pageSize = 20;
  loading = false;
  error = '';
  success = '';
  get messages() {
    return { emptyMessage: tr('SERVICES.SERVICE_LIST.NO_HAY_SERVICIOS_PARA_ESTOS'), totalMessage: tr('COMMON.SERVICES_TOTAL') };
  }

  ngOnInit(): void {
    this.personnel.specialties().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: rows => {
        this.specialties = rows.filter(row => row.active);
        this.specialtiesAvailable = true;
        this.specialty.enable({ emitEvent: false });
      },
      error: () => { this.specialtiesAvailable = false; },
    });
    this.reload$.pipe(startWith(undefined), switchMap(() => {
      this.loading = true;
      this.error = '';
      const params = { search: this.state.search,
        active: this.state.status === 'all' ? undefined : this.state.status === 'active',
        page: this.state.pageIndex + 1, pageSize: this.pageSize,
        ...(this.state.specialtyId ? { specialtyId: this.state.specialtyId } : {}) };
      return this.api.list(params).pipe(
        catchError((error: ServiceApiError) => {
          if (!error.invalidPage || this.state.pageIndex === 0) return throwError(() => error);
          // A state change in this view or its detail can remove the last row of a saved page.
          this.state.pageIndex = 0;
          return this.api.list({ ...params, page: 1 });
        }),
        catchError((error: ServiceApiError) => {
          this.error = error.message; this.rows = []; this.total = 0; return EMPTY;
        }), finalize(() => this.loading = false));
    }), takeUntilDestroyed(this.destroyRef)).subscribe(page => {
      this.rows = page.results; this.total = page.count;
      if (!this.rows.length && this.state.pageIndex > 0) { this.state.pageIndex = 0; this.reload(); }
    });
    this.search.valueChanges.pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(value => { this.state.search = value.trim(); this.state.pageIndex = 0; this.reload(); });
    this.status.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(value => {
      this.state.status = value; this.state.pageIndex = 0; this.reload();
    });
    this.specialty.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(value => {
      this.state.specialtyId = value; this.state.pageIndex = 0; this.reload();
    });
  }
  reload(): void { this.reload$.next(); }
  onPage(event: { offset: number }): void {
    if (this.loading || event.offset === this.state.pageIndex) return;
    this.state.pageIndex = event.offset; this.reload();
  }
  clearFilters(): void {
    this.search.setValue('', { emitEvent: false }); this.status.setValue('active', { emitEvent: false });
    this.specialty.setValue('', { emitEvent: false });
    this.state.search = ''; this.state.status = 'active'; this.state.specialtyId = '';
    this.state.pageIndex = 0; this.reload();
  }
  onUpdated(service: CatalogService): void {
    this.success = service.active ? tr('SERVICES.SERVICE_TOGGLE.SERVICIO_ACTIVADO') : tr('SERVICES.SERVICE_TOGGLE.SERVICIO_DESACTIVADO');
    this.reload();
  }
}
