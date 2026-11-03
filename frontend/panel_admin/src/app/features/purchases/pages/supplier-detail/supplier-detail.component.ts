import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
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
  imports: [TranslatePipe, RouterLink, DatePipe],
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
        this.toastr.success(updated.active ? tr('PURCHASES.SUPPLIER_DETAIL.PROVEEDOR_ACTIVADO') : tr('PURCHASES.SUPPLIER_DETAIL.PROVEEDOR_DESACTIVADO'));
      },
      error: (err: SupplierApiError) => this.toastr.error(err.message),
    });
  }

  /** Confirmación previa a cambiar el estado; separada para poder sustituirla en pruebas. */
  protected async confirmToggle(supplier: Supplier): Promise<boolean> {
    const verb = supplier.active ? tr('COMMON.VERB_DEACTIVATE') : tr('COMMON.VERB_ACTIVATE');
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
}
