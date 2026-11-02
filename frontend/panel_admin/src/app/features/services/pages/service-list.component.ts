import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, finalize, startWith, switchMap } from 'rxjs';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { ServiceToggleComponent } from '../components/service-toggle.component';
import { CatalogService, ServiceApiError } from '../models/service';
import { ServiceFiltersState, ServicesApiService } from '../services/services-api.service';

@Component({ selector: 'app-service-list',
  imports: [ReactiveFormsModule, RouterLink, NgxDatatableModule, MoneyPipe, ServiceToggleComponent],
  templateUrl: './service-list.component.html',
})
export class ServiceListComponent implements OnInit {
  readonly state = inject(ServiceFiltersState);
  private api = inject(ServicesApiService);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();
  search = new FormControl(this.state.search, { nonNullable: true });
  status = new FormControl(this.state.status, { nonNullable: true });
  rows: CatalogService[] = [];
  total = 0;
  pageSize = 20;
  loading = false;
  error = '';
  success = '';
  readonly messages = { emptyMessage: 'No hay servicios para estos filtros.', totalMessage: 'servicios' };

  ngOnInit(): void {
    this.reload$.pipe(startWith(undefined), switchMap(() => {
      this.loading = true;
      this.error = '';
      return this.api.list({ search: this.state.search,
        active: this.state.status === 'all' ? undefined : this.state.status === 'active',
        page: this.state.pageIndex + 1, pageSize: this.pageSize }).pipe(
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
  }
  reload(): void { this.reload$.next(); }
  onPage(event: { offset: number }): void {
    if (this.loading || event.offset === this.state.pageIndex) return;
    this.state.pageIndex = event.offset; this.reload();
  }
  clearFilters(): void {
    this.search.setValue('', { emitEvent: false }); this.status.setValue('active', { emitEvent: false });
    this.state.search = ''; this.state.status = 'active'; this.state.pageIndex = 0; this.reload();
  }
  onUpdated(service: CatalogService): void {
    this.success = service.active ? 'Servicio activado.' : 'Servicio desactivado.';
    this.reload();
  }
}
