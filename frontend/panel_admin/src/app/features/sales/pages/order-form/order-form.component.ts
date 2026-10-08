import { AsyncPipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgFooterTemplateDirective, NgSelectComponent } from '@ng-select/ng-select';
import { ToastrService } from 'ngx-toastr';
import { Observable, Subject, concat, debounceTime, distinctUntilChanged, finalize, switchMap, tap } from 'rxjs';
import {
  Order,
  OrderApiError,
  OrderCustomer,
  OrderErrorField,
  OrderInput,
  SALES_CHANNELS,
  SALES_CHANNEL_LABELS,
  SalesChannel,
  todayIso,
} from '../../models/order';
import { CustomerQuickCreateService } from '../../../customers';
import { CustomerOptionsService } from '../../services/customer-options.service';
import { OrdersApiService } from '../../services/orders-api.service';

export const NOTES_MAX_LENGTH = 2000;
export const NOT_EDITABLE_MESSAGE = 'El pedido ya no admite cambios.';

export type FormField = Extract<
  OrderErrorField,
  'customerId' | 'salesChannel' | 'orderDate' | 'expectedDeliveryDate' | 'notes'
>;

/** Datos del pedido: cliente, canal, fechas y notas. Los productos, el descuento y los pagos se gestionan en el detalle. */
@Component({
  selector: 'app-order-form',
  templateUrl: './order-form.component.html',
  imports: [ReactiveFormsModule, RouterLink, AsyncPipe, NgSelectComponent, NgFooterTemplateDirective],
})
export class OrderFormComponent implements OnInit {
  readonly notesMaxLength = NOTES_MAX_LENGTH;
  readonly channels = SALES_CHANNELS;
  readonly channelLabels = SALES_CHANNEL_LABELS;
  readonly form = inject(FormBuilder).nonNullable.group({
    customer: [null as OrderCustomer | null],
    salesChannel: ['' as SalesChannel | '', Validators.required],
    orderDate: [todayIso(), Validators.required],
    expectedDeliveryDate: [''],
    notes: ['', Validators.maxLength(NOTES_MAX_LENGTH)],
  });

  orderId: string | null = null;
  saving = false;
  loading = false;
  /** Errores del servidor por campo; se limpian al editar. */
  serverErrors: Partial<Record<FormField, string>> = {};

  readonly customerInput$ = new Subject<string>();
  customersLoading = false;
  readonly customers$: Observable<OrderCustomer[]>;

  private ordersApi = inject(OrdersApiService);
  private customerOptions = inject(CustomerOptionsService);
  private quickCreate = inject(CustomerQuickCreateService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    // Solo clientes activos: lista inicial y búsqueda remota por nombre o teléfono.
    this.customers$ = concat(
      this.searchCustomers(''),
      this.customerInput$.pipe(
        debounceTime(300),
        distinctUntilChanged(),
        tap(() => (this.customersLoading = true)),
        switchMap((term) => this.searchCustomers(term)),
      ),
    );
    this.destroyRef.onDestroy(() => this.customerInput$.complete());
  }

  get isEdit(): boolean {
    return this.orderId !== null;
  }

  ngOnInit(): void {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => (this.serverErrors = {}));
    this.orderId = this.route.snapshot.paramMap.get('id');
    if (this.orderId) {
      this.loading = true;
      this.ordersApi
        .get(this.orderId)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (order) => this.fill(order),
          error: (err: OrderApiError) => {
            this.loading = false;
            this.toastr.error(err.message);
            this.router.navigate(['/sales/orders']);
          },
        });
    }
  }

  hasError(field: FormField): boolean {
    const control = this.form.controls[field === 'customerId' ? 'customer' : field];
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverErrors[field];
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const input: OrderInput = {
      customerId: value.customer?.id ?? null,
      salesChannel: value.salesChannel as SalesChannel,
      orderDate: value.orderDate,
      expectedDeliveryDate: value.expectedDeliveryDate || null,
      notes: value.notes.trim(),
    };
    this.saving = true;
    const request = this.orderId ? this.ordersApi.update(this.orderId, input) : this.ordersApi.create(input);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (order) => {
        this.saving = false;
        this.toastr.success(this.isEdit ? 'Pedido actualizado' : 'Pedido creado');
        this.router.navigate(['/sales/orders', order.id]);
      },
      error: (err: OrderApiError) => {
        this.saving = false;
        this.showServerError(err);
      },
    });
  }

  /** Crea un cliente sin salir del pedido (modal) y lo deja seleccionado. */
  async createCustomer(): Promise<void> {
    const customer = await this.quickCreate.open();
    if (customer) {
      this.selectCustomer({ id: customer.id, name: customer.name });
    }
  }

  /** Selecciona un cliente recién creado (creación rápida) como cliente del pedido. */
  selectCustomer(customer: OrderCustomer): void {
    this.form.controls.customer.setValue(customer);
  }

  private searchCustomers(term: string): Observable<OrderCustomer[]> {
    return this.customerOptions.search(term).pipe(finalize(() => (this.customersLoading = false)));
  }

  private fill(order: Order): void {
    if (!order.editable) {
      this.toastr.error(NOT_EDITABLE_MESSAGE);
      this.router.navigate(['/sales/orders', order.id]);
      return;
    }
    this.form.setValue({
      customer: order.customer,
      salesChannel: order.salesChannel,
      orderDate: order.orderDate,
      expectedDeliveryDate: order.expectedDeliveryDate ?? '',
      notes: order.notes,
    });
    this.serverErrors = {};
    this.loading = false;
  }

  private showServerError(err: OrderApiError): void {
    const errors: Partial<Record<FormField, string>> = {};
    for (const field of ['customerId', 'salesChannel', 'orderDate', 'expectedDeliveryDate', 'notes'] as const) {
      const messages = err.fieldErrors[field];
      if (messages?.length) {
        errors[field] = messages.join(' ');
      }
    }
    this.serverErrors = errors;
    if (!Object.keys(errors).length) {
      this.toastr.error(err.message);
    }
  }
}
