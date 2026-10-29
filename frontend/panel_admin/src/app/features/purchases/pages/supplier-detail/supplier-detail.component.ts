import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import Swal from 'sweetalert2';
import { Supplier, SupplierApiError } from '../../models/supplier';
import { SuppliersApiService } from '../../services/suppliers-api.service';

@Component({
  selector: 'app-supplier-detail',
  templateUrl: './supplier-detail.component.html',
  imports: [RouterLink, DatePipe],
})
export class SupplierDetailComponent implements OnInit {
  supplier: Supplier | null = null;
  loading = true;

  private api = inject(SuppliersApiService);
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
        next: (supplier) => {
          this.supplier = supplier;
          this.loading = false;
        },
        error: (err: SupplierApiError) => {
          this.loading = false;
          this.toastr.error(err.message);
          this.router.navigate(['/pocketbiz/purchases/suppliers']);
        },
      });
  }

  async toggleActive(): Promise<void> {
    const supplier = this.supplier;
    if (!supplier || !(await this.confirmToggle(supplier))) {
      return;
    }
    const request = supplier.active ? this.api.deactivate(supplier.id) : this.api.activate(supplier.id);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.supplier = updated;
        this.toastr.success(updated.active ? 'Proveedor activado' : 'Proveedor desactivado');
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
}
