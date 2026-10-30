import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgSelectComponent } from '@ng-select/ng-select';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { EMPTY, Observable, Subject, catchError, debounceTime, finalize, map, of, startWith, switchMap } from 'rxjs';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import {
  PAYMENT_STATUS_CLASSES,
  PAYMENT_STATUS_LABELS,
  PURCHASE_STATUS_CLASSES,
  PURCHASE_STATUS_LABELS,
  PaymentStatus,
  PurchaseApiError,
  PurchaseStatus,
  PurchaseSummary,
  RECEPTION_STATUS_CLASSES,
  RECEPTION_STATUS_LABELS,
  ReceptionStatus,
} from '../../models/purchase';
import { Supplier } from '../../models/supplier';
import { PurchasesApiService } from '../../services/purchases-api.service';
import { SuppliersApiService } from '../../services/suppliers-api.service';
import {
  EMPTY_FILTERS,
  PAYMENT_OPTIONS,
  PurchaseListFilters,
  RECEPTION_OPTIONS,
  STATUS_OPTIONS,
  describeFilters,
  filtersFromParams,
  filtersToApi,
  filtersToQuery,
  hasActiveFilters,
  isRangeInvalid,
} from './purchase-list-filters';

const LIST_PATH = '/pocketbiz/purchases';
const FILTER_DEBOUNCE_MS = 300;

/** Lista de compras con seguimiento de recepción, pago y saldo. Los filtros viven en la URL. */
@Component({
  selector: 'app-purchase-list',
  templateUrl: './purchase-list.component.html',
  styleUrl: './purchase-list.component.scss',
  imports: [RouterLink, ReactiveFormsModule, NgSelectComponent, AsyncPipe, NgxDatatableModule, DatePipe, MoneyPipe],
})
export class PurchaseListComponent implements OnInit {
  readonly pageSize = 10;
  readonly statusOptions = STATUS_OPTIONS;
  readonly receptionOptions = RECEPTION_OPTIONS;
  readonly paymentOptions = PAYMENT_OPTIONS;
  rows: PurchaseSummary[] = [];
  total = 0;
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;
  errorMessage = '';
  filters: PurchaseListFilters = EMPTY_FILTERS;
  supplierName = '';
  rangeInvalid = false;

  readonly filterForm = inject(FormBuilder).nonNullable.group({
    search: '',
    supplier: null as Supplier | null,
    dateFrom: '',
    dateTo: '',
    status: '' as PurchaseListFilters['status'],
    receptionStatus: '' as PurchaseListFilters['receptionStatus'],
    paymentStatus: '' as PurchaseListFilters['paymentStatus'],
  });

  private api = inject(PurchasesApiService);
  private suppliersApi = inject(SuppliersApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();
  readonly supplierInput$ = new Subject<string>();

  /** Proveedores para el selector de filtro; se consultan al escribir. */
  readonly suppliers$: Observable<Supplier[]> = this.supplierInput$.pipe(
    startWith(''),
    debounceTime(200),
    switchMap((term) =>
      this.suppliersApi.list({ search: term || undefined, pageSize: 20 }).pipe(
        map((page) => page.results),
        catchError(() => of([] as Supplier[])),
      ),
    ),
  );

  get filtersActive(): boolean {
    return hasActiveFilters(this.filters);
  }

  /** Filtros aplicados en texto, para el vacío con filtros. */
  get appliedFilters(): string[] {
    return describeFilters(this.filters, this.supplierName);
  }

  get emptyWithFilters(): boolean {
    return !this.loading && !this.errorMessage && this.rows.length === 0 && this.filtersActive;
  }

  get messages(): { emptyMessage: string; totalMessage: string } {
    return { emptyMessage: 'Aún no hay compras. Crea la primera con «Nueva compra».', totalMessage: 'en total' };
  }

  ngOnInit(): void {
    this.reload$
      .pipe(
        switchMap(() => {
          this.loading = true;
          this.errorMessage = '';
          return this.api.list({ ...filtersToApi(this.filters), page: this.pageIndex + 1, pageSize: this.pageSize }).pipe(
            catchError((err: PurchaseApiError) => {
              this.errorMessage = err.message;
              return EMPTY;
            }),
            finalize(() => (this.loading = false)),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        this.rows = page.results;
        this.total = page.count;
      });

    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      this.filters = filtersFromParams(params);
      this.pageIndex = 0;
      this.rangeInvalid = false;
      this.syncForm();
      this.reload$.next();
    });

    this.filterForm.valueChanges
      .pipe(debounceTime(FILTER_DEBOUNCE_MS), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.applyForm());
  }

  /** Pasa lo escrito en el formulario a la URL (que dispara la consulta). Un rango invertido no consulta. */
  applyForm(): void {
    const value = this.filterForm.getRawValue();
    const next: PurchaseListFilters = {
      supplierId: value.supplier?.id ?? '',
      dateFrom: value.dateFrom,
      dateTo: value.dateTo,
      status: value.status,
      receptionStatus: value.receptionStatus,
      paymentStatus: value.paymentStatus,
      search: value.search,
    };
    this.rangeInvalid = isRangeInvalid(next);
    if (this.rangeInvalid) {
      return;
    }
    void this.router.navigate([LIST_PATH], { queryParams: filtersToQuery(next) });
  }

  clearFilters(): void {
    void this.router.navigate([LIST_PATH]);
  }

  onPage(event: { offset: number }): void {
    // ngx-datatable también emite `page` al inicializarse; sin cambio de página no se vuelve a pedir.
    if (event.offset === this.pageIndex) {
      return;
    }
    this.pageIndex = event.offset;
    this.reload$.next();
  }

  statusClass(status: PurchaseStatus): string {
    return PURCHASE_STATUS_CLASSES[status];
  }

  statusLabel(status: PurchaseStatus): string {
    return PURCHASE_STATUS_LABELS[status];
  }

  receptionClass(status: ReceptionStatus): string {
    return RECEPTION_STATUS_CLASSES[status];
  }

  receptionLabel(status: ReceptionStatus): string {
    return RECEPTION_STATUS_LABELS[status];
  }

  paymentClass(status: PaymentStatus): string {
    return PAYMENT_STATUS_CLASSES[status];
  }

  paymentLabel(status: PaymentStatus): string {
    return PAYMENT_STATUS_LABELS[status];
  }

  retry(): void {
    this.reload$.next();
  }

  /** Refleja los filtros de la URL en el formulario sin volver a disparar la consulta. */
  private syncForm(): void {
    const current = this.filterForm.controls.supplier.value;
    const keepSupplier = current !== null && current.id === this.filters.supplierId;
    this.filterForm.patchValue(
      {
        search: this.filters.search,
        supplier: keepSupplier ? current : null,
        dateFrom: this.filters.dateFrom,
        dateTo: this.filters.dateTo,
        status: this.filters.status,
        receptionStatus: this.filters.receptionStatus,
        paymentStatus: this.filters.paymentStatus,
      },
      { emitEvent: false },
    );
    this.supplierName = keepSupplier && current ? current.name : '';
    if (this.filters.supplierId && !keepSupplier) {
      this.loadSupplier(this.filters.supplierId);
    }
  }

  private loadSupplier(id: string): void {
    this.suppliersApi
      .get(id)
      .pipe(
        catchError(() => EMPTY),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((supplier) => {
        if (this.filters.supplierId === id) {
          this.supplierName = supplier.name;
          this.filterForm.controls.supplier.setValue(supplier, { emitEvent: false });
        }
      });
  }
}
