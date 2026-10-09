import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import Swal from 'sweetalert2';
import { CustomerPurchaseHistoryComponent } from '../../components/customer-purchase-history/customer-purchase-history.component';
import { Customer, CustomerApiError, CustomerOrderSummary } from '../../models/customer';
import { CustomerOrdersApiService } from '../../services/customer-orders-api.service';
import { CustomersApiService } from '../../services/customers-api.service';

@Component({
  selector: 'app-customer-detail',
  templateUrl: './customer-detail.component.html',
  imports: [RouterLink, DatePipe, CustomerPurchaseHistoryComponent],
})
export class CustomerDetailComponent implements OnInit {
  customer: Customer | null = null;
  loading = true;
  /** Pedidos del cliente, cargados desde Sales (ADR historial-compras) una vez conocido el cliente. */
  orders: CustomerOrderSummary[] = [];
  ordersTotal = 0;
  ordersLoading = false;
  /** Un fallo del historial no impide ver los datos del cliente. */
  ordersError = '';

  private api = inject(CustomersApiService);
  private ordersApi = inject(CustomerOrdersApiService);
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
        next: (customer) => {
          this.customer = customer;
          this.loading = false;
          this.loadOrders(customer.id);
        },
        error: (err: CustomerApiError) => {
          this.loading = false;
          this.toastr.error(err.message);
          this.router.navigate(['/customers']);
        },
      });
  }

  private loadOrders(customerId: string): void {
    this.ordersLoading = true;
    this.ordersError = '';
    this.ordersApi
      .list(customerId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (history) => {
          this.orders = history.orders;
          this.ordersTotal = history.total;
          this.ordersLoading = false;
        },
        error: (err: Error) => {
          this.ordersError = err.message;
          this.ordersLoading = false;
        },
      });
  }

  async toggleActive(): Promise<void> {
    const customer = this.customer;
    if (!customer || !(await this.confirmToggle(customer))) {
      return;
    }
    const request = customer.active ? this.api.deactivate(customer.id) : this.api.activate(customer.id);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.customer = updated;
        this.toastr.success(updated.active ? 'Cliente activado' : 'Cliente desactivado');
      },
      error: (err: CustomerApiError) => this.toastr.error(err.message),
    });
  }

  /** Confirmación previa a cambiar el estado; separada para poder sustituirla en pruebas. */
  protected async confirmToggle(customer: Customer): Promise<boolean> {
    const verb = customer.active ? 'desactivar' : 'activar';
    const result = await Swal.fire({
      titleText: `¿Quieres ${verb} a "${customer.name}"?`,
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
}
