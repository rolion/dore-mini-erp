import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, finalize, switchMap } from 'rxjs';
import Swal from 'sweetalert2';
import { Customer, CustomerApiError } from '../../models/customer';
import { CustomersApiService } from '../../services/customers-api.service';

export type StatusFilter = 'all' | 'active' | 'inactive';

@Component({
  selector: 'app-customer-list',
  templateUrl: './customer-list.component.html',
  styleUrl: './customer-list.component.scss',
  imports: [TranslatePipe, RouterLink, NgxDatatableModule, ReactiveFormsModule],
})
export class CustomerListComponent implements OnInit {
  readonly pageSize = 10;
  readonly messages = { emptyMessage: tr('CUSTOMERS.CUSTOMER_LIST.NO_HAY_CLIENTES_QUE_COINCIDAN'), totalMessage: tr('COMMON.IN_TOTAL') };
  readonly searchControl = new FormControl('', { nonNullable: true });
  /** Los clientes desactivados no aparecen por defecto (REQ-CUS-005). */
  readonly statusControl = new FormControl<StatusFilter>('active', { nonNullable: true });

  rows: Customer[] = [];
  total = 0;
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;

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
              search: this.searchControl.value.trim(),
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

    this.searchControl.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.goToFirstPageAndReload());
    this.statusControl.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.goToFirstPageAndReload());

    this.reload$.next();
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
    switch (this.statusControl.value) {
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
    this.reload$.next();
  }
}
