import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { BreakpointObserver } from '@angular/cdk/layout';
import { NgTemplateOutlet } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbCollapse, NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, finalize, merge, switchMap } from 'rxjs';
import Swal from 'sweetalert2';
import { ModulesService } from '../../../../core/service/modules.service';
import { PRODUCT_CATEGORIES, Product, ProductApiError, ProductCategory, categoryLabel } from '../../models/product';
import { ProductUsesComponent } from '../../../../shared/components/product-uses/product-uses.component';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { ProductsApiService } from '../../services/products-api.service';

/** Por debajo de 957 px la lista pasa a tarjetas y los filtros a un panel colapsable que se aplica a mano. */
export const COMPACT_QUERY = '(max-width: 956.98px)';

export type StatusFilter = 'all' | 'active' | 'inactive';
export type UseFilter = 'all' | 'buy' | 'sell';
export type CategoryFilter = 'all' | 'unclassified' | ProductCategory;

@Component({
  selector: 'app-product-list',
  templateUrl: './product-list.component.html',
  styleUrl: './product-list.component.scss',
  imports: [NgTemplateOutlet, TranslatePipe, RouterLink, NgbCollapse, NgbPagination, ReactiveFormsModule, ProductUsesComponent, MoneyPipe],
})
export class ProductListComponent implements OnInit {
  readonly pageSize = 10;
  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly statusControl = new FormControl<StatusFilter>('all', { nonNullable: true });
  readonly useControl = new FormControl<UseFilter>('all', { nonNullable: true });
  readonly categoryControl = new FormControl<CategoryFilter>('all', { nonNullable: true });
  readonly categories = PRODUCT_CATEGORIES;

  rows: Product[] = [];
  total = 0;
  /** Página actual, base 1 como espera `ngb-pagination`. */
  page = 1;
  loading = false;
  /** Pantalla estrecha (< 957 px): tarjetas y filtros en un panel colapsable que se aplica con «Aplicar». */
  compact = false;
  filtersCollapsed = true;

  private breakpoints = inject(BreakpointObserver);
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
              page: this.page,
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
      .subscribe(() => this.applyOnDesktop());
    merge(this.statusControl.valueChanges, this.useControl.valueChanges, this.categoryControl.valueChanges)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.applyOnDesktop());
    this.breakpoints
      .observe(COMPACT_QUERY)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => (this.compact = state.matches));

    this.reload$.next();
  }

  /** Cuántos filtros se apartan de su valor por defecto (contador del botón «Filtros»). */
  get activeFilterCount(): number {
    return [
      this.searchControl.value.trim() !== '',
      this.statusControl.value !== 'all',
      this.useControl.value !== 'all',
      this.categoryControl.value !== 'all',
    ].filter(Boolean).length;
  }

  toggleFilters(): void {
    this.filtersCollapsed = !this.filtersCollapsed;
  }

  /** Consulta con los filtros del formulario y repliega el panel para mostrar las tarjetas. */
  applyFilters(): void {
    this.filtersCollapsed = true;
    this.goToFirstPageAndReload();
  }

  clearFilters(): void {
    this.searchControl.setValue('', { emitEvent: false });
    this.statusControl.setValue('all', { emitEvent: false });
    this.useControl.setValue('all', { emitEvent: false });
    this.categoryControl.setValue('all', { emitEvent: false });
    this.applyFilters();
  }

  categoryName(product: Product): string {
    return categoryLabel(product.category);
  }

  goTo(page: number): void {
    if (page === this.page) {
      return;
    }
    this.page = page;
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

  /** En escritorio los filtros se aplican al instante; en pantalla estrecha, con «Aplicar». */
  private applyOnDesktop(): void {
    if (!this.compact) {
      this.goToFirstPageAndReload();
    }
  }

  private goToFirstPageAndReload(): void {
    this.page = 1;
    this.reload$.next();
  }
}
