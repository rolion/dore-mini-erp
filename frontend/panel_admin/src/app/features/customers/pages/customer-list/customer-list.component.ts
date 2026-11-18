import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { BreakpointObserver } from '@angular/cdk/layout';
import { NgTemplateOutlet } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbCollapse, NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, finalize, switchMap } from 'rxjs';
import Swal from 'sweetalert2';
import { Customer, CustomerApiError } from '../../models/customer';
import { CustomersApiService } from '../../services/customers-api.service';

export type StatusFilter = 'all' | 'active' | 'inactive';

/** Por debajo de `lg` (992 px) los filtros son un panel colapsable con «Aplicar» y las filas son tarjetas. */
export const COMPACT_QUERY = '(max-width: 991.98px)';

const DEFAULT_STATUS: StatusFilter = 'active';

@Component({
  selector: 'app-customer-list',
  templateUrl: './customer-list.component.html',
  styleUrl: './customer-list.component.scss',
  imports: [TranslatePipe, RouterLink, NgxDatatableModule, ReactiveFormsModule, NgbCollapse, NgbPagination, NgTemplateOutlet],
})
export class CustomerListComponent implements OnInit {
  readonly pageSize = 10;
  get messages() {
    return { emptyMessage: tr('CUSTOMERS.CUSTOMER_LIST.NO_HAY_CLIENTES_QUE_COINCIDAN'), totalMessage: tr('COMMON.IN_TOTAL') };
  }
  readonly searchControl = new FormControl('', { nonNullable: true });
  /** Los clientes desactivados no aparecen por defecto (REQ-CUS-005). */
  readonly statusControl = new FormControl<StatusFilter>(DEFAULT_STATUS, { nonNullable: true });

  rows: Customer[] = [];
  total = 0;
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;
  /** Pantalla estrecha: tarjetas en vez de tabla y filtros con «Aplicar». */
  compact = false;
  filtersCollapsed = true;
  /** Filtros que se enviaron al servidor (en pantalla estrecha pueden diferir de lo escrito hasta pulsar «Aplicar»). */
  private applied = { search: '', status: DEFAULT_STATUS as StatusFilter };

  private breakpoints = inject(BreakpointObserver);
  private api = inject(CustomersApiService);
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
              active: this.activeFilter(),
              page: this.pageIndex + 1,
              pageSize: this.pageSize,
            })
            .pipe(
              catchError((err: CustomerApiError) => {
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

    this.breakpoints
      .observe(COMPACT_QUERY)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => (this.compact = state.matches));

    // En pantalla estrecha los cambios se aplican con «Aplicar»; en escritorio, al instante.
    this.searchControl.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.applyIfWide());
    this.statusControl.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.applyIfWide());

    this.reload$.next();
  }

  /** Cuántos filtros se apartan de su valor por defecto (contador del botón «Filtros»). */
  get activeFilterCount(): number {
    return (this.searchControl.value.trim() ? 1 : 0) + (this.statusControl.value !== DEFAULT_STATUS ? 1 : 0);
  }

  toggleFilters(): void {
    this.filtersCollapsed = !this.filtersCollapsed;
  }

  /** Consulta con lo escrito en los filtros y repliega el panel para mostrar las tarjetas. */
  applyFilters(): void {
    this.filtersCollapsed = true;
    this.syncAppliedAndReload();
  }

  clearFilters(): void {
    this.searchControl.setValue('', { emitEvent: false });
    this.statusControl.setValue(DEFAULT_STATUS, { emitEvent: false });
    this.applyFilters();
  }

  /** Página (base 1) para `ngb-pagination` en la vista de tarjetas. */
  onCardsPage(page: number): void {
    this.onPage({ offset: page - 1 });
  }

  onPage(event: { offset: number }): void {
    // ngx-datatable también emite `page` al inicializarse; sin cambio de página no se vuelve a pedir.
    if (event.offset === this.pageIndex) {
      return;
    }
    this.pageIndex = event.offset;
    this.reload$.next();
  }

  async toggleActive(customer: Customer): Promise<void> {
    if (!(await this.confirmToggle(customer))) {
      return;
    }
    const request = customer.active ? this.api.deactivate(customer.id) : this.api.activate(customer.id);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.toastr.success(updated.active ? tr('CUSTOMERS.CUSTOMER_DETAIL.CLIENTE_ACTIVADO') : tr('CUSTOMERS.CUSTOMER_DETAIL.CLIENTE_DESACTIVADO'));
        this.reload$.next();
      },
      error: (err: CustomerApiError) => this.toastr.error(err.message),
    });
  }

  /** Confirmación previa a cambiar el estado; separada para poder sustituirla en pruebas. */
  protected async confirmToggle(customer: Customer): Promise<boolean> {
    const verb = customer.active ? tr('COMMON.VERB_DEACTIVATE') : tr('COMMON.VERB_ACTIVATE');
    const result = await Swal.fire({
      titleText: tr('CUSTOMERS.CUSTOMER_DETAIL.QUIERES_A', { p0: verb, p1: customer.name }),
      text: customer.active
        ? tr('CUSTOMERS.CUSTOMER_DETAIL.DEJARA_DE_APARECER_ENTRE_LOS')
        : tr('CUSTOMERS.CUSTOMER_DETAIL.VOLVERA_A_APARECER_ENTRE_LOS'),
      showCancelButton: true,
      confirmButtonColor: '#8963ff',
      cancelButtonColor: '#fb7823',
      confirmButtonText: tr('CUSTOMERS.CUSTOMER_DETAIL.SI'),
      cancelButtonText: tr('CUSTOMERS.CUSTOMER_QUICK_CREATE.CANCELAR'),
    });
    return result.isConfirmed;
  }

  private activeFilter(): boolean | undefined {
    switch (this.applied.status) {
      case 'active':
        return true;
      case 'inactive':
        return false;
      default:
        return undefined;
    }
  }

  private applyIfWide(): void {
    if (!this.compact) {
      this.syncAppliedAndReload();
    }
  }

  private syncAppliedAndReload(): void {
    this.applied = { search: this.searchControl.value.trim(), status: this.statusControl.value };
    this.pageIndex = 0;
    this.reload$.next();
  }
}
