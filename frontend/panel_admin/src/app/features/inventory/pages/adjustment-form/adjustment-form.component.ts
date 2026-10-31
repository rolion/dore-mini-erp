import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgSelectComponent } from '@ng-select/ng-select';
import { ToastrService } from 'ngx-toastr';
import {
  EMPTY,
  Subject,
  catchError,
  combineLatest,
  debounceTime,
  distinctUntilChanged,
  filter,
  merge,
  of,
  startWith,
  switchMap,
  take,
  tap,
} from 'rxjs';
import { HasUnsavedChanges } from '../../../../core/guard/unsaved-changes.guard';
import { ModulesService } from '../../../../core/service/modules.service';
import {
  ADJUSTMENT_REASON_MAX_LENGTH,
  AdjustmentBalance,
  AdjustmentInput,
  differenceOf,
  directionOf,
  signedDifference,
} from '../../models/adjustment';
import { FieldErrors, InsufficientStockInfo, InventoryApiError } from '../../models/api-error';
import { InsufficientStockAlertComponent } from '../../components/insufficient-stock-alert/insufficient-stock-alert.component';
import { MovementKind } from '../../models/movement';
import { OpeningProduct, formatQuantity, newUuid, quantityError } from '../../models/stock';
import { Warehouse } from '../../models/warehouse';
import { AdjustmentsApiService } from '../../services/adjustments-api.service';
import { OpeningProductsService } from '../../services/opening-products.service';
import { stockReturnLink } from '../../services/stock-return';
import { ValuationApiService } from '../../services/valuation-api.service';
import { WarehousesApiService } from '../../services/warehouses-api.service';

export type AdjustmentStep = 'edit' | 'review';
export type AdjustmentField = 'warehouseId' | 'productId' | 'countedQuantity' | 'reason' | 'totalValue';

export const ADJUSTMENT_SUCCESS_MESSAGE = 'Ajuste registrado';
export const NO_DIFFERENCE_MESSAGE = 'Sin diferencia: no se registrará ningún movimiento.';

/** Nuevo ajuste: producto, almacén, cantidad contada y motivo; revisión y confirmación de envío único. */
@Component({
  selector: 'app-adjustment-form',
  templateUrl: './adjustment-form.component.html',
  imports: [ReactiveFormsModule, RouterLink, NgSelectComponent, InsufficientStockAlertComponent],
})
export class AdjustmentFormComponent implements OnInit, HasUnsavedChanges {
  readonly reasonMaxLength = ADJUSTMENT_REASON_MAX_LENGTH;
  private readonly fb = inject(FormBuilder).nonNullable;

  readonly form = this.fb.group({
    warehouseId: ['', Validators.required],
    product: this.fb.control<OpeningProduct | null>(null, Validators.required),
    countedQuantity: [''],
    reason: ['', [Validators.required, Validators.maxLength(ADJUSTMENT_REASON_MAX_LENGTH)]],
    totalValue: [''],
    declaredZero: [false],
  });

  /** Inventario valorado: el ajuste positivo necesita un valor. Se sabe con Costeo habilitado o al exigirlo el servidor. */
  valuedInventory = false;

  step: AdjustmentStep = 'edit';
  warehouses: Warehouse[] = [];
  productOptions: OpeningProduct[] = [];
  productsLoading = false;
  readonly productInput$ = new Subject<string>();
  /** Saldo del sistema que la persona está viendo; es el «saldo esperado» que se envía al confirmar. */
  balance: AdjustmentBalance | null = null;
  balanceLoading = false;
  saving = false;
  /** Aviso de un saldo que cambió desde el conteo (409 `balance_changed`). */
  balanceNotice = '';
  conflictMessage = '';
  /** Salida rechazada por saldo insuficiente (409 `insufficient_stock`); el formulario conserva sus datos. */
  insufficientStock: InsufficientStockInfo | null = null;
  serverErrors: Partial<Record<AdjustmentField, string>> = {};
  /** Una vez confirmado no hay nada que perder al salir. */
  completed = false;

  /** Clave de idempotencia: se genera al abrir el formulario y se reenvía en cada intento de confirmación. */
  private readonly adjustmentId = newUuid();
  private preselectedProductId: string | null = null;
  /** Detalle de existencia al que volver (si se llegó desde él). */
  readonly returnLink = stockReturnLink(inject(ActivatedRoute).snapshot.queryParamMap);

  private api = inject(AdjustmentsApiService);
  private warehousesApi = inject(WarehousesApiService);
  private modules = inject(ModulesService);
  private valuationApi = inject(ValuationApiService);
  private productsApi = inject(OpeningProductsService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.preselectedProductId = this.route.snapshot.queryParamMap.get('product_id');
    this.loadWarehouses();
    this.detectValuedInventory();
    this.watchProducts();
    this.watchBalance();
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.serverErrors = {};
      this.conflictMessage = '';
      this.insufficientStock = null;
    });
  }

  hasUnsavedChanges(): boolean {
    return !this.completed && this.form.dirty;
  }

  sameProduct = (a: OpeningProduct, b: OpeningProduct): boolean => a.id === b.id;

  get product(): OpeningProduct | null {
    return this.form.controls.product.value;
  }

  get unitLabel(): string {
    return this.balance?.unit?.abbreviation ?? this.product?.unit.abbreviation ?? '';
  }

  get allowsFractions(): boolean {
    return this.balance?.unit?.allowsFractions ?? this.product?.unit.allowsFractions ?? true;
  }

  get balanceText(): string {
    return this.balance ? formatQuantity(this.balance.systemQuantity) : '';
  }

  get countedText(): string {
    return this.form.controls.countedQuantity.value.trim();
  }

  /** Mensaje de la cantidad contada (del servidor o del cliente), o `null`. */
  get countedMessage(): string | null {
    const server = this.serverErrors.countedQuantity;
    if (server) {
      return server;
    }
    const control = this.form.controls.countedQuantity;
    if (!control.touched && !control.dirty) {
      return null;
    }
    return quantityError(control.value, this.allowsFractions);
  }

  get reasonMessage(): string | null {
    const server = this.serverErrors.reason;
    if (server) {
      return server;
    }
    const control = this.form.controls.reason;
    if (!(control.touched || control.dirty)) {
      return null;
    }
    if (control.errors?.['maxlength']) {
      return `El motivo no puede superar ${ADJUSTMENT_REASON_MAX_LENGTH} caracteres.`;
    }
    return control.value.trim() ? null : 'El motivo es obligatorio.';
  }

  message(field: 'warehouseId' | 'productId'): string | null {
    const server = this.serverErrors[field];
    if (server) {
      return server;
    }
    const control = field === 'warehouseId' ? this.form.controls.warehouseId : this.form.controls.product;
    if (!(control.invalid && (control.touched || control.dirty))) {
      return null;
    }
    return field === 'warehouseId' ? 'Elige un almacén.' : 'Elige un producto.';
  }

  /** Diferencia contada − saldo (texto con signo), o `null` mientras falte el saldo o la cantidad no sea válida. */
  get difference(): string | null {
    if (!this.balance || quantityError(this.countedText, this.allowsFractions) !== null) {
      return null;
    }
    return differenceOf(this.countedText, this.balance.systemQuantity);
  }

  get differenceText(): string {
    return this.difference === null ? '' : signedDifference(this.difference);
  }

  get direction(): MovementKind | null {
    return this.difference === null ? null : directionOf(this.difference);
  }

  get noDifference(): boolean {
    return this.difference !== null && this.direction === null;
  }

  /** El valor se pide solo con inventario valorado y una diferencia positiva (entrada de ajuste). */
  get needsValue(): boolean {
    return this.valuedInventory && this.direction === 'in';
  }

  get valueMessage(): string | null {
    const server = this.serverErrors.totalValue;
    if (server) {
      return server;
    }
    const control = this.form.controls.totalValue;
    if (!this.needsValue || !(control.touched || control.dirty)) {
      return null;
    }
    return this.valueProblem;
  }

  /** Problema del valor ingresado (importe en BOB con hasta 2 decimales, o costo cero declarado), o `null`. */
  private get valueProblem(): string | null {
    const { totalValue, declaredZero } = this.form.getRawValue();
    const text = totalValue.trim();
    if (declaredZero) {
      return text && Number(text) !== 0 ? 'Un costo cero declarado no admite un valor distinto de cero.' : null;
    }
    if (!text) {
      return 'Ingresa el valor total del ajuste en BOB o declara costo cero.';
    }
    if (!/^\d+(\.\d{1,2})?$/.test(text)) {
      return 'El valor debe ser un importe en BOB con hasta 2 decimales.';
    }
    return Number(text) === 0 ? 'Un costo cero debe declararse explícitamente.' : null;
  }

  get canReview(): boolean {
    return (
      this.form.valid &&
      !(this.needsValue && this.valueProblem !== null) &&
      !!this.form.controls.reason.value.trim() &&
      this.balance !== null &&
      this.difference !== null &&
      !this.noDifference &&
      !this.balanceLoading &&
      !this.saving
    );
  }

  get canConfirm(): boolean {
    return this.canReview;
  }

  get warehouseName(): string {
    return this.warehouses.find((w) => w.id === this.form.controls.warehouseId.value)?.name ?? '';
  }

  review(): void {
    this.form.markAllAsTouched();
    if (!this.canReview) {
      return;
    }
    this.step = 'review';
  }

  backToEdit(): void {
    this.step = 'edit';
    this.balanceNotice = '';
  }

  confirm(): void {
    // Un segundo clic (o Enter) mientras la petición sigue en curso no envía nada.
    if (this.saving || !this.canConfirm) {
      return;
    }
    this.saving = true;
    this.balanceNotice = '';
    this.insufficientStock = null;
    this.api
      .confirm(this.buildInput())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (adjustment) => {
          this.completed = true;
          this.toastr.success(ADJUSTMENT_SUCCESS_MESSAGE);
          if (this.returnLink) {
            this.router.navigate(this.returnLink);
          } else {
            this.router.navigate(['/pocketbiz/inventory/adjustments', adjustment.id]);
          }
        },
        error: (err: InventoryApiError) => {
          this.saving = false;
          this.showServerError(err);
        },
      });
  }

  private buildInput(): AdjustmentInput {
    const value = this.form.getRawValue();
    return {
      adjustmentId: this.adjustmentId,
      productId: value.product?.id ?? '',
      warehouseId: value.warehouseId,
      countedQuantity: value.countedQuantity.trim(),
      expectedSystemQuantity: this.balance?.systemQuantity ?? '0',
      reason: value.reason.trim(),
      ...(this.needsValue
        ? { totalValue: value.declaredZero ? '0' : value.totalValue.trim(), declaredZero: value.declaredZero }
        : {}),
    };
  }

  /** Costeo habilitado y con valoración adoptada: los ajustes positivos se valoran. */
  private detectValuedInventory(): void {
    this.modules.enabledKeys$
      .pipe(
        filter((keys): keys is ReadonlySet<string> => keys !== null),
        take(1),
        switchMap((keys) => (keys.has('costing') ? this.valuationApi.get() : EMPTY)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({ next: (valuation) => (this.valuedInventory = valuation.status === 'adopted'), error: () => undefined });
  }

  private showServerError(err: InventoryApiError): void {
    if (err.status === 409 && err.code === 'balance_changed' && err.currentBalance !== null && this.balance) {
      // El saldo cambió desde el conteo: se muestra el nuevo y se exige revisar y reconfirmar (no se reenvía solo).
      const previous = this.balanceText;
      this.balance = { ...this.balance, systemQuantity: err.currentBalance };
      this.step = 'review';
      const diff = this.difference;
      const effect =
        diff === null || directionOf(diff) === null
          ? 'Ahora no hay diferencia.'
          : `La diferencia ahora es ${signedDifference(diff)} ${this.unitLabel}.`;
      this.balanceNotice = `El saldo cambió de ${previous} a ${this.balanceText} desde tu conteo. ${effect}`;
      return;
    }
    this.step = 'edit';
    if (err.status === 409 && err.code === 'insufficient_stock' && err.insufficientStock) {
      this.insufficientStock = err.insufficientStock;
      return;
    }
    if (err.status === 400) {
      this.serverErrors = this.toFieldMessages(err.fieldErrors);
      if (this.serverErrors.totalValue) {
        this.valuedInventory = true; // el servidor exige un valor: se muestra el campo aunque Costeo esté deshabilitado
      }
      if (!Object.keys(this.serverErrors).length) {
        this.conflictMessage = err.message;
      }
      return;
    }
    this.conflictMessage = err.message;
  }

  private toFieldMessages(errors: FieldErrors): Partial<Record<AdjustmentField, string>> {
    const result: Partial<Record<AdjustmentField, string>> = {};
    for (const field of ['warehouseId', 'productId', 'countedQuantity', 'reason', 'totalValue'] as const) {
      const messages = errors[field];
      if (messages?.length) {
        result[field] = messages.join(' ');
      }
    }
    return result;
  }

  private loadWarehouses(): void {
    this.warehousesApi
      .list({ active: true, pageSize: 100 })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (page) => {
          this.warehouses = page.results;
          const requested = this.route.snapshot.queryParamMap.get('warehouse_id');
          const preferred =
            page.results.find((w) => w.id === requested) ?? page.results.find((w) => w.isDefault) ?? page.results[0];
          if (preferred) {
            // Preselección: no cuenta como cambio de la persona.
            this.form.controls.warehouseId.setValue(preferred.id);
            this.form.markAsPristine();
          }
        },
        error: (err: InventoryApiError) => (this.conflictMessage = err.message),
      });
  }

  private watchProducts(): void {
    merge(of(''), this.productInput$.pipe(debounceTime(300), distinctUntilChanged()))
      .pipe(
        tap(() => (this.productsLoading = true)),
        switchMap((term) => this.productsApi.search(term)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((products) => {
        this.productOptions = products;
        this.productsLoading = false;
        const wanted = this.preselectedProductId;
        const match = wanted ? products.find((p) => p.id === wanted) : undefined;
        if (match && !this.product) {
          this.preselectedProductId = null;
          this.form.controls.product.setValue(match);
          this.form.markAsPristine();
        }
      });
  }

  /** Al elegir almacén y producto se consulta el saldo vigente (solo lectura en el formulario). */
  private watchBalance(): void {
    combineLatest([
      this.form.controls.warehouseId.valueChanges.pipe(startWith(this.form.controls.warehouseId.value)),
      this.form.controls.product.valueChanges.pipe(startWith(this.form.controls.product.value)),
    ])
      .pipe(
        tap(() => {
          this.balance = null;
          this.balanceNotice = '';
        }),
        switchMap(([warehouseId, product]) => {
          if (!warehouseId || !product) {
            return of(null);
          }
          this.balanceLoading = true;
          return this.api.balance(product.id, warehouseId).pipe(
            catchError((err: InventoryApiError) => {
              this.conflictMessage = err.message;
              return of(null);
            }),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((balance) => {
        this.balance = balance;
        this.balanceLoading = false;
      });
  }
}
