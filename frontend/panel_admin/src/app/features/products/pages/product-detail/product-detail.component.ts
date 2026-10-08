import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import Swal from 'sweetalert2';
import { Product, ProductApiError } from '../../models/product';
import { ProductsApiService } from '../../services/products-api.service';

@Component({
  selector: 'app-product-detail',
  templateUrl: './product-detail.component.html',
  imports: [RouterLink, DatePipe],
})
export class ProductDetailComponent implements OnInit {
  product: Product | null = null;
  loading = true;

  private api = inject(ProductsApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

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
          this.router.navigate(['/catalog/products']);
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
        this.toastr.success(updated.active ? 'Producto activado' : 'Producto desactivado');
      },
      error: (err: ProductApiError) => this.toastr.error(err.message),
    });
  }

  /** Confirmación previa a cambiar el estado; separada para poder sustituirla en pruebas. */
  protected async confirmToggle(product: Product): Promise<boolean> {
    const verb = product.active ? 'desactivar' : 'activar';
    const result = await Swal.fire({
      title: `¿Quieres ${verb} "${product.name}"?`,
      text: product.active ? 'Dejará de poder agregarse a nuevos pedidos.' : 'Volverá a estar disponible para la venta.',
      showCancelButton: true,
      confirmButtonColor: '#8963ff',
      cancelButtonColor: '#fb7823',
      confirmButtonText: 'Sí',
      cancelButtonText: 'Cancelar',
    });
    return result.isConfirmed;
  }
}
