import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, finalize, switchMap } from 'rxjs';
import Swal from 'sweetalert2';
import { Supplier, SupplierApiError } from '../../models/supplier';
import { SuppliersApiService } from '../../services/suppliers-api.service';

export type StatusFilter = 'all' | 'active' | 'inactive';

@Component({
  selector: 'app-supplier-list',
  templateUrl: './supplier-list.component.html',
  styleUrl: './supplier-list.component.scss',
  imports: [RouterLink, NgxDatatableModule, ReactiveFormsModule],
})
export class SupplierListComponent implements OnInit {
  readonly pageSize = 10;
  readonly messages = { emptyMessage: 'No hay proveedores que coincidan', totalMessage: 'en total' };
  readonly searchControl = new FormControl('', { nonNullable: true });
  /** Los proveedores desactivados no aparecen por defecto. */
  readonly statusControl = new FormControl<StatusFilter>('active', { nonNullable: true });

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
              search: this.searchControl.value.trim(),
              active: this.activeFilter(),
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

  async toggleActive(supplier: Supplier): Promise<void> {
    if (!(await this.confirmToggle(supplier))) {
      return;
    }
    const request = supplier.active ? this.api.deactivate(supplier.id) : this.api.activate(supplier.id);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.toastr.success(updated.active ? 'Proveedor activado' : 'Proveedor desactivado');
        this.reload$.next();
      },
      error: (err: SupplierApiError) => this.toastr.error(err.message),
    });
  }

  /** Confirmación previa a cambiar el estado; separada para poder sustituirla en pruebas. */
  protected async confirmToggle(supplier: Supplier): Promise<boolean> {
    const verb = supplier.active ? 'desactivar' : 'activar';
    const result = await Swal.fire({
      titleText: `¿Quieres ${verb} a "${supplier.name}"?`,
      text: supplier.active
        ? 'Dejará de ofrecerse en compras nuevas. Sus compras históricas se conservan.'
        : 'Volverá a ofrecerse en compras nuevas.',
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
