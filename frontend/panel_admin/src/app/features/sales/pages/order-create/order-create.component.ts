import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { AsyncPipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgFooterTemplateDirective, NgOptionTemplateDirective, NgSelectComponent } from '@ng-select/ng-select';
import { ToastrService } from 'ngx-toastr';
import {
  Observable,
  Subject,
  catchError,
  concat,
  debounceTime,
  defer,
  distinctUntilChanged,
  finalize,
  map,
  of,
  switchMap,
  tap,
} from 'rxjs';
import { HasUnsavedChanges } from '../../../../core/guard/unsaved-changes.guard';
import { ModulesService } from '../../../../core/service/modules.service';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { CustomerQuickCreateService } from '../../../customers';
import { Warehouse, WarehousesApiService } from '../../../inventory';
import { Product, ProductsApiService } from '../../../products';
import {
  FieldErrors,
  OrderApiError,
  OrderCustomer,
  OrderRuleError,
  SALES_CHANNELS,
  SALES_CHANNEL_LABELS,
  SalesChannel,
  StartOrderInput,
  StockShortage,
  todayIso,
} from '../../models/order';
import { CustomerOptionsService } from '../../services/customer-options.service';
import {
  DiscountProblem,
  discountProblem,
  formatCents,
  lineSubtotal,
  maxDiscountAmount,
  subtotalCents,
  totalCents,
} from '../../services/order-amounts';
import { OrdersApiService } from '../../services/orders-api.service';
import { DEFAULT_MAX_DISCOUNT_PERCENT, SalesSettingsService } from '../../services/sales-settings.service';

export const NOTES_MAX_LENGTH = 2000;
export const PRODUCT_SEARCH_PAGE_SIZE = 20;
const WAREHOUSE_PAGE_SIZE = 100;

/** Línea del borrador: el precio mostrado es el del catálogo al agregarla; el servidor fija el definitivo al crear. */
export interface DraftLine {
  productId: string;
  productName: string;
  unitPrice: string;
  quantity: number;
  tracksStock: boolean;
}

type HeaderField = 'customerId' | 'salesChannel' | 'orderDate' | 'expectedDeliveryDate' | 'notes' | 'warehouseId';

/**
 * Pantalla única de creación del pedido: cabecera, detalle de productos, descuento y totales. Nada se guarda hasta
 * «Iniciar preparación», que crea el pedido completo en preparación. Los importes son informativos (manda el servidor).
 */
@Component({
  selector: 'app-order-create',
  templateUrl: './order-create.component.html',
  imports: [
    TranslatePipe,
    ReactiveFormsModule,
    RouterLink,
    AsyncPipe,
    NgSelectComponent,
    NgFooterTemplateDirective,
    NgOptionTemplateDirective,
    MoneyPipe,
  ],
})
export class OrderCreateComponent implements OnInit, HasUnsavedChanges {
  readonly notesMaxLength = NOTES_MAX_LENGTH;
  readonly channels = SALES_CHANNELS;
  readonly channelLabels = SALES_CHANNEL_LABELS;

  private fb = inject(FormBuilder).nonNullable;
  readonly form = this.fb.group({
    customer: [null as OrderCustomer | null],
    salesChannel: ['' as SalesChannel | '', Validators.required],
    orderDate: [todayIso(), Validators.required],
    expectedDeliveryDate: [''],
    warehouseId: [''],
    notes: ['', Validators.maxLength(NOTES_MAX_LENGTH)],
  });
  readonly addForm = this.fb.group({
    product: [null as Product | null, Validators.required],
    quantity: [1, [Validators.required, Validators.min(1)]],
  });
  readonly discountControl = new FormControl('', { nonNullable: true });

  lines: DraftLine[] = [];
  warehouses: Warehouse[] = [];
  warehousesLoaded = false;
  maxDiscountPercent = DEFAULT_MAX_DISCOUNT_PERCENT;
  saving = false;
  /** Errores del servidor por campo; se limpian al editar. */
  serverErrors: Partial<Record<HeaderField | 'items' | 'discount', string>> = {};
  /** Faltantes de un 409 `insufficient_stock`: dejan la fila marcada y un aviso con el detalle. */
  shortages: StockShortage[] = [];
  shortageWarehouse = '';

  readonly customerInput$ = new Subject<string>();
  customersLoading = false;
  readonly customers$: Observable<OrderCustomer[]>;
  readonly productInput$ = new Subject<string>();
  productsLoading = false;
  readonly products$: Observable<Product[]>;

  private ordersApi = inject(OrdersApiService);
  private salesSettings = inject(SalesSettingsService);
  private customerOptions = inject(CustomerOptionsService);
  private productsApi = inject(ProductsApiService);
  private warehousesApi = inject(WarehousesApiService);
  private modules = inject(ModulesService);
  private quickCreate = inject(CustomerQuickCreateService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);
  private saved = false;

  constructor() {
    this.customers$ = concat(
      this.searchCustomers(''),
      this.customerInput$.pipe(
        debounceTime(300),
        distinctUntilChanged(),
        tap(() => (this.customersLoading = true)),
        switchMap((term: string | null) => this.searchCustomers(term)),
      ),
    );
    this.products$ = concat(
      this.searchProducts(''),
      this.productInput$.pipe(
        debounceTime(300),
        distinctUntilChanged(),
        tap(() => (this.productsLoading = true)),
        switchMap((term: string | null) => this.searchProducts(term)),
      ),
    );
    this.destroyRef.onDestroy(() => {
      this.customerInput$.complete();
      this.productInput$.complete();
    });
  }

  // --- módulos opcionales ---------------------------------------------------------------------------------------

  /** Con Clientes deshabilitado no se ofrece el selector de cliente. */
  get customersDisabled(): boolean {
    return this.modules.isDisabled('customers');
  }

  /** Solo con Inventario habilitado se elige almacén y se valida existencia. */
  get inventoryEnabled(): boolean {
    return this.modules.enabledKeysValue?.has('inventory') ?? false;
  }

  /** El almacén es obligatorio solo si algún producto de la tabla controla stock. */
  get warehouseRequired(): boolean {
    return this.inventoryEnabled && this.lines.some((line) => line.tracksStock);
  }

  // --- importes (informativos) ----------------------------------------------------------------------------------

  get subtotal(): string {
    return formatCents(this.subtotalValue);
  }

  get total(): string {
    return formatCents(totalCents(this.subtotalValue, this.discountControl.value));
  }

  get maxDiscount(): string {
    return maxDiscountAmount(this.subtotalValue, this.maxDiscountPercent);
  }

  get percentText(): string {
    return this.maxDiscountPercent.includes('.') ? this.maxDiscountPercent.replace(/\.?0+$/, '') : this.maxDiscountPercent;
  }

  get discountIssue(): DiscountProblem | null {
    return discountProblem(this.discountControl.value, this.subtotalValue, this.maxDiscountPercent);
  }

  lineSubtotalOf(line: DraftLine): string {
    return lineSubtotal(line.unitPrice, line.quantity) ?? '';
  }

  isShort(line: DraftLine): boolean {
    return this.shortages.some((short) => short.productName === line.productName);
  }

  get canSubmit(): boolean {
    const warehouseMissing = this.warehouseRequired && !this.form.controls.warehouseId.value;
    return !this.saving && this.form.valid && this.lines.length > 0 && !warehouseMissing && this.discountIssue === null;
  }

  hasUnsavedChanges(): boolean {
    return !this.saved && (this.form.dirty || this.lines.length > 0 || this.discountControl.dirty);
  }

  ngOnInit(): void {
    const reset = (): void => {
      this.serverErrors = {};
      this.shortages = [];
    };
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(reset);
    this.discountControl.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(reset);
    this.suggestDefaults();
    this.preselectCustomer();
    if (this.inventoryEnabled) {
      this.loadWarehouses();
    }
  }

  hasError(field: HeaderField): boolean {
    const control = this.form.controls[field === 'customerId' ? 'customer' : field];
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverErrors[field];
  }

  // --- detalle ---------------------------------------------------------------------------------------------------

  addLine(): void {
    const { product, quantity } = this.addForm.getRawValue();
    if (this.addForm.invalid || !product) {
      this.addForm.markAllAsTouched();
      return;
    }
    const amount = Math.trunc(Number(quantity));
    if (!(amount >= 1)) return;
    this.shortages = [];
    this.serverErrors = {};
    const existing = this.lines.find((line) => line.productId === product.id);
    if (existing) {
      existing.quantity += amount; // un producto ya listado suma la cantidad: no duplica la fila
    } else {
      this.lines = [
        ...this.lines,
        {
          productId: product.id,
          productName: product.name,
          unitPrice: product.salePrice ?? '0.00',
          quantity: amount,
          tracksStock: product.tracksStock,
        },
      ];
    }
    this.addForm.reset({ product: null, quantity: 1 });
    this.form.markAsDirty();
  }

  changeQuantity(line: DraftLine, input: HTMLInputElement): void {
    const quantity = Number(input.value);
    if (!Number.isInteger(quantity) || quantity < 1) {
      input.value = String(line.quantity);
      return;
    }
    line.quantity = quantity;
    this.shortages = [];
  }

  removeLine(line: DraftLine): void {
    this.lines = this.lines.filter((candidate) => candidate !== line);
    this.shortages = [];
  }

  // --- guardar ---------------------------------------------------------------------------------------------------

  onSubmit(): void {
    if (!this.canSubmit) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const input: StartOrderInput = {
      customerId: value.customer?.id ?? null,
      salesChannel: value.salesChannel as SalesChannel,
      orderDate: value.orderDate,
      expectedDeliveryDate: value.expectedDeliveryDate || null,
      notes: value.notes.trim(),
      warehouseId: this.inventoryEnabled && value.warehouseId ? value.warehouseId : null,
      discount: this.discountControl.value.trim() || '0',
      items: this.lines.map((line) => ({ productId: line.productId, quantity: line.quantity })),
    };
    if (this.customersDisabled) {
      input.customerId = null;
    }
    this.saving = true;
    this.ordersApi
      .start(input)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (order) => {
          this.saving = false;
          this.saved = true;
          this.toastr.success(tr('SALES.ORDER_CREATE.PEDIDO_EN_PREPARACION'));
          this.router.navigate(['/pocketbiz/sales/orders', order.id]);
        },
        error: (err: OrderApiError) => {
          this.saving = false;
          this.showServerError(err);
        },
      });
  }

  async createCustomer(): Promise<void> {
    const customer = await this.quickCreate.open();
    if (customer) {
      this.form.controls.customer.setValue({ id: customer.id, name: customer.name });
    }
  }

  // --- privados --------------------------------------------------------------------------------------------------

  private get subtotalValue(): bigint {
    return subtotalCents(this.lines);
  }

  private searchCustomers(term: string | null): Observable<OrderCustomer[]> {
    return this.customerOptions.search(term).pipe(finalize(() => (this.customersLoading = false)));
  }

  /** `ng-select` emite `null` por el typeahead al elegir o limpiar; un fallo deja la lista vacía sin romper el stream. */
  private searchProducts(term: string | null | undefined): Observable<Product[]> {
    return defer(() =>
      this.productsApi.list({
        search: (term ?? '').trim(),
        active: true,
        canSell: true,
        pageSize: PRODUCT_SEARCH_PAGE_SIZE,
      }),
    ).pipe(
      map((page) => page.results),
      catchError(() => of([] as Product[])),
      finalize(() => (this.productsLoading = false)),
    );
  }

  /** Canal predeterminado de la empresa y tope de descuento; si no se pueden leer, el formulario queda como siempre. */
  private suggestDefaults(): void {
    this.salesSettings
      .defaults()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((defaults) => {
        this.maxDiscountPercent = defaults.maxDiscountPercent;
        const control = this.form.controls.salesChannel;
        if (defaults.salesChannel && control.pristine && control.value === '') {
          control.setValue(defaults.salesChannel);
        }
      });
  }

  /** Un pedido abierto desde el perfil de un cliente (`?customer=<id>&customer_name=<nombre>`) parte con ese cliente. */
  private preselectCustomer(): void {
    const params = this.route.snapshot.queryParamMap;
    const id = params.get('customer');
    if (id && !this.customersDisabled) {
      this.form.controls.customer.setValue({ id, name: params.get('customer_name') ?? '' });
    }
  }

  /** Almacenes activos; se preselecciona el único o el predeterminado (la persona puede cambiarlo). */
  private loadWarehouses(): void {
    this.warehousesApi
      .list({ active: true, pageSize: WAREHOUSE_PAGE_SIZE })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (page) => {
          this.warehouses = page.results;
          this.warehousesLoaded = true;
          const suggested = this.warehouses.length === 1 ? this.warehouses[0] : this.warehouses.find((w) => w.isDefault);
          if (suggested && !this.form.controls.warehouseId.value) {
            this.form.controls.warehouseId.setValue(suggested.id, { emitEvent: false });
          }
        },
        error: () => (this.warehousesLoaded = true),
      });
  }

  private showServerError(err: OrderApiError): void {
    if (err instanceof OrderRuleError && err.code === 'insufficient_stock') {
      this.shortages = err.shortages;
      this.shortageWarehouse = err.warehouseName;
      return;
    }
    if (err.status === 400 && Object.keys(err.fieldErrors).length) {
      this.serverErrors = this.mapFieldErrors(err.fieldErrors);
      return;
    }
    this.toastr.error(err.message);
  }

  private mapFieldErrors(fieldErrors: FieldErrors): Partial<Record<HeaderField | 'items' | 'discount', string>> {
    const errors: Partial<Record<HeaderField | 'items' | 'discount', string>> = {};
    for (const field of [
      'customerId',
      'salesChannel',
      'orderDate',
      'expectedDeliveryDate',
      'notes',
      'warehouseId',
      'items',
      'discount',
    ] as const) {
      const messages = fieldErrors[field];
      if (messages?.length) {
        errors[field] = messages.join(' ');
      }
    }
    return errors;
  }
}
