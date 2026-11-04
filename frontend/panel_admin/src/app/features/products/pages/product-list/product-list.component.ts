import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, finalize, merge, switchMap } from 'rxjs';
import Swal from 'sweetalert2';
import { ModulesService } from '../../../../core/service/modules.service';
import { PRODUCT_CATEGORIES, Product, ProductApiError, ProductCategory, categoryLabel } from '../../models/product';
import { ProductUsesComponent } from '../../../../shared/components/product-uses/product-uses.component';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { ProductsApiService } from '../../services/products-api.service';

export type StatusFilter = 'all' | 'active' | 'inactive';
export type UseFilter = 'all' | 'buy' | 'sell';
export type CategoryFilter = 'all' | 'unclassified' | ProductCategory;

@Component({
  selector: 'app-product-list',
  templateUrl: './product-list.component.html',
  styleUrl: './product-list.component.scss',
  imports: [TranslatePipe, RouterLink, NgxDatatableModule, ReactiveFormsModule, ProductUsesComponent, MoneyPipe],
})
export class ProductListComponent implements OnInit {
  readonly pageSize = 10;
  get messages() {
    return { emptyMessage: tr('PRODUCTS.PRODUCT_LIST.NO_HAY_PRODUCTOS'), totalMessage: tr('COMMON.IN_TOTAL') };
  }
  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly statusControl = new FormControl<StatusFilter>('all', { nonNullable: true });
  readonly useControl = new FormControl<UseFilter>('all', { nonNullable: true });
  readonly categoryControl = new FormControl<CategoryFilter>('all', { nonNullable: true });
  readonly categories = PRODUCT_CATEGORIES;

  rows: Product[] = [];
  total = 0;
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;

  private modules = inject(ModulesService);
  private api = inject(ProductsApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  /** Los datos de inventario se muestran solo cuando el módulo Inventario está habilitado. */
  get inventoryEnabled(): boolean {
    return this.modules.enabledKeysValue?.has('inventory') ?? false;
  }

  ngOnInit(): void {
    this.reload$
      .pipe(
        switchMap(() => {
          this.loading = true;
          return this.api
            .list({
              search: this.searchControl.value.trim(),
              active: this.activeFilter(),
              canBuy: this.useControl.value === 'buy' ? true : undefined,
              canSell: this.useControl.value === 'sell' ? true : undefined,
              category: this.categoryControl.value === 'all' ? undefined : this.categoryControl.value,
              page: this.pageIndex + 1,
              pageSize: this.pageSize,
            })
            .pipe(
              catchError((err: ProductApiError) => {
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
    merge(this.statusControl.valueChanges, this.useControl.valueChanges, this.categoryControl.valueChanges)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.goToFirstPageAndReload());

    this.reload$.next();
  }

  /** Los productos inactivos se atenúan además de llevar su badge de estado. */
  readonly rowClass = (row: Product): Record<string, boolean> => ({ 'text-muted': !row.active });

  categoryName(product: Product): string {
    return categoryLabel(product.category);
  }

  onPage(event: { offset: number }): void {
    // ngx-datatable también emite `page` al inicializarse; sin cambio de página no se vuelve a pedir.
    if (event.offset === this.pageIndex) {
      return;
    }
    this.pageIndex = event.offset;
    this.reload$.next();
  }

  async toggleActive(product: Product): Promise<void> {
    if (!(await this.confirmToggle(product))) {
      return;
    }
    const request = product.active ? this.api.deactivate(product.id) : this.api.activate(product.id);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.toastr.success(updated.active ? tr('PRODUCTS.PRODUCT_DETAIL.PRODUCTO_ACTIVADO') : tr('PRODUCTS.PRODUCT_DETAIL.PRODUCTO_DESACTIVADO'));
        this.reload$.next();
      },
      error: (err: ProductApiError) => this.toastr.error(err.message),
    });
  }

  /** Confirmación previa a cambiar el estado; separada para poder sustituirla en pruebas. */
  protected async confirmToggle(product: Product): Promise<boolean> {
    const verb = product.active ? tr('COMMON.VERB_DEACTIVATE') : tr('COMMON.VERB_ACTIVATE');
    const result = await Swal.fire({
      title: tr('PRODUCTS.PRODUCT_DETAIL.QUIERES', { p0: verb, p1: product.name }),
      text: product.active ? tr('PRODUCTS.PRODUCT_DETAIL.DEJARA_DE_PODER_AGREGARSE_A') : tr('PRODUCTS.PRODUCT_DETAIL.VOLVERA_A_ESTAR_DISPONIBLE_PARA'),
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
