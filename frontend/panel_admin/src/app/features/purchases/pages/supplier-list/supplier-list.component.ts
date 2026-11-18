import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { Component, DestroyRef, ElementRef, OnInit, inject, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, finalize, switchMap } from 'rxjs';
import Swal from 'sweetalert2';
import { CompactViewportService } from '../../../../core/layout/compact-viewport.service';
import { Supplier, SupplierApiError } from '../../models/supplier';
import { SuppliersApiService } from '../../services/suppliers-api.service';

export type StatusFilter = 'all' | 'active' | 'inactive';

@Component({
  selector: 'app-supplier-list',
  templateUrl: './supplier-list.component.html',
  styleUrl: './supplier-list.component.scss',
  imports: [TranslatePipe, RouterLink, NgxDatatableModule, ReactiveFormsModule, NgbPagination],
})
export class SupplierListComponent implements OnInit {
  readonly pageSize = 10;
  get messages() {
    return { emptyMessage: tr('PURCHASES.SUPPLIER_LIST.NO_HAY_PROVEEDORES_QUE_COINCIDAN'), totalMessage: tr('COMMON.IN_TOTAL') };
  }
  readonly searchControl = new FormControl('', { nonNullable: true });
  /** Los proveedores desactivados no aparecen por defecto. */
  readonly statusControl = new FormControl<StatusFilter>('active', { nonNullable: true });

  /** Solo en pantalla estrecha: el panel de filtros se abre con «Filtros» y se cierra al aplicar. */
  filtersOpen = false;
  readonly compact = inject(CompactViewportService).compact;
  private readonly summary = viewChild<ElementRef<HTMLElement>>('summary');
  /** Filtros con los que se pidió la lista; en pantalla estrecha los controles pueden ir por delante hasta pulsar «Aplicar». */
  private applied: { search: string; status: StatusFilter } = { search: '', status: 'active' };

  rows: Supplier[] = [];
  total = 0;
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;

  private api = inject(SuppliersApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  ngOnInit(): void {
    this.reload$
      .pipe(
        switchMap(() => {
          this.loading = true;
          return this.api
            .list({
              search: this.applied.search,
              active: this.activeFilter(this.applied.status),
              page: this.pageIndex + 1,
              pageSize: this.pageSize,
            })
            .pipe(
              catchError((err: SupplierApiError) => {
                this.toastr.error(err.message);
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

    this.searchControl.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.applyIfWide());
    this.statusControl.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.applyIfWide());

    this.reload$.next();
  }

  /** Filtros aplicados que se resumen como chips al cerrar el panel. */
  get appliedFilters(): string[] {
    const chips: string[] = [];
    if (this.applied.search) chips.push(tr('PURCHASES.SUPPLIER_LIST.BUSCAR_FILTRO', { value: this.applied.search }));
    if (this.applied.status !== 'active') {
      chips.push(tr('PURCHASES.SUPPLIER_LIST.ESTADO_FILTRO', { value: this.statusLabel(this.applied.status) }));
    }
    return chips;
  }

  get activeFilterCount(): number {
    return this.appliedFilters.length;
  }

  /** Hay algo distinto del estado inicial en los controles (habilita «Limpiar filtros»). */
  get filtersActive(): boolean {
    return this.searchControl.value.trim() !== '' || this.statusControl.value !== 'active';
  }

  /** Rango visible para «Mostrando 1–10 de N». */
  get shownFrom(): number {
    return this.rows.length === 0 ? 0 : this.pageIndex * this.pageSize + 1;
  }

  get shownTo(): number {
    return this.pageIndex * this.pageSize + this.rows.length;
  }

  /** «Aplicar» en pantalla estrecha: aplica, cierra el panel y lleva el foco al resumen de resultados. */
  applyAndClose(): void {
    this.goToFirstPageAndReload();
    this.filtersOpen = false;
    queueMicrotask(() => this.summary()?.nativeElement.focus());
  }

  clearFilters(): void {
    this.searchControl.setValue('', { emitEvent: false });
    this.statusControl.setValue('active', { emitEvent: false });
    this.filtersOpen = false;
    this.goToFirstPageAndReload();
  }

  /** Paginación de las tarjetas (`ngb-pagination` es base 1) y vuelta al inicio de la lista. */
  onPageNumber(page: number): void {
    this.onPage({ offset: page - 1 });
    queueMicrotask(() => {
      const el = this.summary()?.nativeElement;
      el?.scrollIntoView({ block: 'start' });
      el?.focus();
    });
  }

  actionLabel(actionKey: string, supplier: Supplier): string {
    return tr('PURCHASES.SUPPLIER_LIST.ACCION_SOBRE_N', { action: tr(actionKey), name: supplier.name });
  }

  onPage(event: { offset: number }): void {
    // ngx-datatable también emite `page` al inicializarse; sin cambio de página no se vuelve a pedir.
    if (event.offset === this.pageIndex) {
      return;
    }
    this.pageIndex = event.offset;
    this.reload$.next();
  }

  async toggleActive(supplier: Supplier): Promise<void> {
    if (!(await this.confirmToggle(supplier))) {
      return;
    }
    const request = supplier.active ? this.api.deactivate(supplier.id) : this.api.activate(supplier.id);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.toastr.success(updated.active ? tr('PURCHASES.SUPPLIER_DETAIL.PROVEEDOR_ACTIVADO') : tr('PURCHASES.SUPPLIER_DETAIL.PROVEEDOR_DESACTIVADO'));
        this.reload$.next();
      },
      error: (err: SupplierApiError) => this.toastr.error(err.message),
    });
  }

  /** Confirmación previa a cambiar el estado; separada para poder sustituirla en pruebas. */
  protected async confirmToggle(supplier: Supplier): Promise<boolean> {
    const verb = supplier.active ? 'desactivar' : 'activar';
    const result = await Swal.fire({
      titleText: tr('CUSTOMERS.CUSTOMER_DETAIL.QUIERES_A', { p0: verb, p1: supplier.name }),
      text: supplier.active
        ? tr('PURCHASES.SUPPLIER_DETAIL.DEJARA_DE_OFRECERSE_EN_COMPRAS')
        : tr('PURCHASES.SUPPLIER_DETAIL.VOLVERA_A_OFRECERSE_EN_COMPRAS'),
      showCancelButton: true,
      confirmButtonColor: '#8963ff',
      cancelButtonColor: '#fb7823',
      confirmButtonText: tr('CUSTOMERS.CUSTOMER_DETAIL.SI'),
      cancelButtonText: tr('CUSTOMERS.CUSTOMER_QUICK_CREATE.CANCELAR'),
    });
    return result.isConfirmed;
  }

  private statusLabel(status: StatusFilter): string {
    return tr(status === 'active' ? 'COMMON.ACTIVOS' : status === 'inactive' ? 'COMMON.INACTIVOS' : 'COMMON.TODOS');
  }

  /** En escritorio los filtros se aplican al cambiar; en pantalla estrecha, con el botón «Aplicar». */
  private applyIfWide(): void {
    if (!this.compact()) this.goToFirstPageAndReload();
  }

  private activeFilter(status: StatusFilter): boolean | undefined {
    switch (status) {
      case 'active':
        return true;
      case 'inactive':
        return false;
      default:
        return undefined;
    }
  }

  private goToFirstPageAndReload(): void {
    this.pageIndex = 0;
    this.applied = { search: this.searchControl.value.trim(), status: this.statusControl.value };
    this.reload$.next();
  }
}
