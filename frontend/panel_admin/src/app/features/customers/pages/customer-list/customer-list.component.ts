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
  imports: [RouterLink, NgxDatatableModule, ReactiveFormsModule],
})
export class CustomerListComponent implements OnInit {
  readonly pageSize = 10;
  readonly messages = { emptyMessage: 'No hay clientes que coincidan', totalMessage: 'en total' };
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
        this.toastr.success(updated.active ? 'Cliente activado' : 'Cliente desactivado');
        this.reload$.next();
      },
      error: (err: CustomerApiError) => this.toastr.error(err.message),
    });
  }

  /** Confirmación previa a cambiar el estado; separada para poder sustituirla en pruebas. */
  protected async confirmToggle(customer: Customer): Promise<boolean> {
    const verb = customer.active ? 'desactivar' : 'activar';
    const result = await Swal.fire({
      title: `¿Quieres ${verb} a "${customer.name}"?`,
      text: customer.active
        ? 'Dejará de aparecer entre los clientes activos. Su historial de pedidos se conserva.'
        : 'Volverá a aparecer entre los clientes activos.',
      showCancelButton: true,
      confirmButtonColor: '#8963ff',
      cancelButtonColor: '#fb7823',
      confirmButtonText: 'Sí',
      cancelButtonText: 'Cancelar',
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
