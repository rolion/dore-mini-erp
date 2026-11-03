import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import Swal from 'sweetalert2';
import { ModulesService } from '../../../../core/service/modules.service';
import { Product, ProductApiError, categoryLabel } from '../../models/product';
import { ProductsApiService } from '../../services/products-api.service';

@Component({
  selector: 'app-product-detail',
  templateUrl: './product-detail.component.html',
  imports: [TranslatePipe, RouterLink, DatePipe],
})
export class ProductDetailComponent implements OnInit {
  product: Product | null = null;
  loading = true;

  private modules = inject(ModulesService);
  private api = inject(ProductsApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  /** Los datos de inventario se muestran solo cuando el módulo Inventario está habilitado. */
  get inventoryEnabled(): boolean {
    return this.modules.enabledKeysValue?.has('inventory') ?? false;
  }

  categoryName(product: Product): string {
    return categoryLabel(product.category);
  }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.api
      .get(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (product) => {
          this.product = product;
          this.loading = false;
        },
        error: (err: ProductApiError) => {
          this.loading = false;
          this.toastr.error(err.message);
          this.router.navigate(['/pocketbiz/catalog/products']);
        },
      });
  }

  async toggleActive(): Promise<void> {
    const product = this.product;
    if (!product || !(await this.confirmToggle(product))) {
      return;
    }
    const request = product.active ? this.api.deactivate(product.id) : this.api.activate(product.id);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.product = updated;
        this.toastr.success(updated.active ? tr('PRODUCTS.PRODUCT_DETAIL.PRODUCTO_ACTIVADO') : tr('PRODUCTS.PRODUCT_DETAIL.PRODUCTO_DESACTIVADO'));
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
}
