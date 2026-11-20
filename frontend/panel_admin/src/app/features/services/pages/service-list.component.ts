import { tr } from '../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { BreakpointObserver } from '@angular/cdk/layout';
import { NgTemplateOutlet } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbCollapse, NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { EMPTY, Subject, catchError, finalize, startWith, switchMap, throwError } from 'rxjs';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { SpecialtyOption } from '../../personnel/models/profile';
import { PersonnelApiService } from '../../personnel/services/personnel-api.service';
import { ServiceToggleComponent } from '../components/service-toggle.component';
import { CatalogService, ServiceApiError } from '../models/service';
import { ServiceFiltersState, ServicesApiService } from '../services/services-api.service';

/** Por debajo de 957 px la lista pasa a tarjetas y los filtros a un panel plegable. */
export const COMPACT_QUERY = '(max-width: 956.98px)';

@Component({ selector: 'app-service-list',
  imports: [NgTemplateOutlet, TranslatePipe, ReactiveFormsModule, RouterLink, NgbCollapse, NgbPagination, MoneyPipe, ServiceToggleComponent],
  templateUrl: './service-list.component.html',
  styleUrl: './service-list.component.scss',
})
export class ServiceListComponent implements OnInit {
  readonly state = inject(ServiceFiltersState);
  private breakpoints = inject(BreakpointObserver);
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
  /** Los filtros arrancan plegados; «Aplicar» consulta y los repliega para dejar las tarjetas a la vista. */
  filtersCollapsed = true;
  /** Pantalla estrecha (< 957 px): tarjetas y filtros plegables; desde 957 px, tabla y filtros siempre visibles. */
  compact = false;

  ngOnInit(): void {
    this.breakpoints.observe(COMPACT_QUERY).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(state => this.compact = state.matches);
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
  }
  reload(): void { this.reload$.next(); }
  onPage(page: number): void {
    if (this.loading || page - 1 === this.state.pageIndex) return;
    this.state.pageIndex = page - 1; this.reload();
  }
  /** Cuántos filtros se apartan de su valor por defecto (contador del botón «Filtros»). */
  get activeFilterCount(): number {
    return (this.state.search ? 1 : 0) + (this.state.status !== 'active' ? 1 : 0) + (this.state.specialtyId ? 1 : 0);
  }
  toggleFilters(): void { this.filtersCollapsed = !this.filtersCollapsed; }
  applyFilters(): void {
    this.state.search = this.search.value.trim(); this.state.status = this.status.value; this.state.specialtyId = this.specialty.value;
    this.state.pageIndex = 0; this.filtersCollapsed = true; this.reload();
  }
  clearFilters(): void {
    this.search.setValue('', { emitEvent: false }); this.status.setValue('active', { emitEvent: false });
    this.specialty.setValue('', { emitEvent: false });
    this.state.search = ''; this.state.status = 'active'; this.state.specialtyId = '';
    this.state.pageIndex = 0; this.filtersCollapsed = true; this.reload();
  }
  onUpdated(service: CatalogService): void {
    this.success = service.active ? tr('SERVICES.SERVICE_TOGGLE.SERVICIO_ACTIVADO') : tr('SERVICES.SERVICE_TOGGLE.SERVICIO_DESACTIVADO');
    this.reload();
  }
}
