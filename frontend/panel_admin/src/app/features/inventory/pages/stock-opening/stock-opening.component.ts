import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormArray, FormBuilder, FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgSelectComponent } from '@ng-select/ng-select';
import { ToastrService } from 'ngx-toastr';
import { Subject, catchError, debounceTime, distinctUntilChanged, merge, of, startWith, switchMap, tap } from 'rxjs';
import { HasUnsavedChanges } from '../../../../core/guard/unsaved-changes.guard';
import { FieldErrors, InventoryApiError } from '../../models/api-error';
import {
  OPENING_REFERENCE_MAX_LENGTH,
  OpeningInput,
  OpeningProduct,
  formatQuantity,
  newUuid,
  quantityError,
  todayIso,
} from '../../models/stock';
import { Warehouse } from '../../models/warehouse';
import { stockReturnLink } from '../../services/stock-return';
import { OpeningProductsService } from '../../services/opening-products.service';
import { StockApiService } from '../../services/stock-api.service';
import { WarehousesApiService } from '../../services/warehouses-api.service';

export type OpeningStep = 'edit' | 'review';
export type HeaderField = 'warehouseId' | 'movementDate' | 'reference';

export const DUPLICATE_MESSAGE = 'Este producto ya está en otra línea.';
export const HISTORY_MESSAGE = 'Ya tiene movimientos en este almacén; corrígelo con un ajuste.';
export const OPENING_SUCCESS_MESSAGE = 'Apertura registrada';

type LineGroup = FormGroup<{ product: FormControl<OpeningProduct | null>; quantity: FormControl<string> }>;

export interface SummaryLine {
  name: string;
  quantity: string;
  unit: string;
}

/** Registrar apertura: almacén, fecha, referencia y líneas; revisión del resumen y confirmación de envío único. */
@Component({
  selector: 'app-stock-opening',
  templateUrl: './stock-opening.component.html',
  styleUrl: './stock-opening.component.scss',
  imports: [ReactiveFormsModule, RouterLink, NgSelectComponent, DatePipe],
})
export class StockOpeningComponent implements OnInit, HasUnsavedChanges {
  readonly referenceMaxLength = OPENING_REFERENCE_MAX_LENGTH;
  readonly today = todayIso();
  private readonly fb = inject(FormBuilder).nonNullable;

  readonly form = this.fb.group({
    warehouseId: ['', Validators.required],
    movementDate: [todayIso(), Validators.required],
    reference: ['', [Validators.required, Validators.maxLength(OPENING_REFERENCE_MAX_LENGTH)]],
    lines: this.fb.array<LineGroup>([]),
  });

  step: OpeningStep = 'edit';
  warehouses: Warehouse[] = [];
  productOptions: OpeningProduct[] = [];
  productsLoading = false;
  readonly productInput$ = new Subject<string>();
  /** Productos de las líneas que ya tienen movimientos en el almacén elegido. */
  historyIds = new Set<string>();
  checking = false;
  saving = false;
  /** Mensaje de un rechazo de regla del servidor (409) o de un error general. */
  conflictMessage = '';
  serverErrors: Partial<Record<HeaderField, string>> = {};
  serverLineErrors: FieldErrors[] = [];
  /** Una vez confirmada no hay nada que perder al salir. */
  completed = false;

  /** Clave de idempotencia: se genera al abrir el formulario y se reenvía en cada intento de confirmación. */
  private readonly openingId = newUuid();
  private baseOptions: OpeningProduct[] = [];
  private check$ = new Subject<void>();

  private stockApi = inject(StockApiService);
  private warehousesApi = inject(WarehousesApiService);
  /** Detalle de existencia al que volver (si se llegó desde él) y producto a preseleccionar. */
  readonly returnLink = stockReturnLink(inject(ActivatedRoute).snapshot.queryParamMap);
  private preselectedProductId: string | null = null;

  private productsApi = inject(OpeningProductsService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  get lines(): FormArray<LineGroup> {
    return this.form.controls.lines;
  }

  ngOnInit(): void {
    this.preselectedProductId = this.route.snapshot.queryParamMap.get('product_id');
    this.addLine();
    this.loadWarehouses();
    this.watchProducts();
    this.watchHistory();
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.serverErrors = {};
      this.serverLineErrors = [];
      this.conflictMessage = '';
    });
    this.form.controls.warehouseId.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.check$.next());
  }

  hasUnsavedChanges(): boolean {
    return !this.completed && this.form.dirty;
  }

  addLine(): void {
    this.lines.push(
      this.fb.group({
        product: this.fb.control<OpeningProduct | null>(null, Validators.required),
        quantity: this.fb.control(''),
      }),
    );
    this.refreshOptions();
  }

  removeLine(index: number): void {
    if (this.lines.length <= 1) {
      return;
    }
    this.lines.removeAt(index);
    this.form.markAsDirty();
    this.onProductsChanged();
  }

  onProductsChanged(): void {
    this.refreshOptions();
    this.check$.next();
  }

  sameProduct = (a: OpeningProduct, b: OpeningProduct): boolean => a.id === b.id;

  productAt(index: number): OpeningProduct | null {
    return this.lines.at(index).controls.product.value;
  }

  /** La línea repite un producto ya elegido más arriba. */
  isDuplicate(index: number): boolean {
    const product = this.productAt(index);
    return !!product && this.lines.controls.some((_, i) => i < index && this.productAt(i)?.id === product.id);
  }

  hasHistory(index: number): boolean {
    const product = this.productAt(index);
    return !!product && this.historyIds.has(product.id);
  }

  /** Mensaje de la cantidad de una línea (del cliente o del servidor), o `null`. */
  quantityMessage(index: number): string | null {
    const server = this.serverLineErrors[index]?.['quantity']?.join(' ');
    if (server) {
      return server;
    }
    const group = this.lines.at(index);
    const product = group.controls.product.value;
    if (!group.controls.quantity.touched && !group.controls.quantity.dirty) {
      return null;
    }
    return quantityError(group.controls.quantity.value, product?.unit.allowsFractions ?? true);
  }

  productMessage(index: number): string | null {
    const server = this.serverLineErrors[index]?.['productId']?.join(' ');
    if (server) {
      return server;
    }
    if (this.isDuplicate(index)) {
      return DUPLICATE_MESSAGE;
    }
    return this.hasHistory(index) ? HISTORY_MESSAGE : null;
  }

  headerMessage(field: HeaderField): string | null {
    const server = this.serverErrors[field];
    if (server) {
      return server;
    }
    const control = this.form.controls[field];
    if (!(control.invalid && (control.touched || control.dirty))) {
      return null;
    }
    const required: Record<HeaderField, string> = {
      warehouseId: 'Elige un almacén.',
      movementDate: 'La fecha es obligatoria.',
      reference: 'La referencia de apertura es obligatoria.',
    };
    return control.errors?.['maxlength']
      ? `La referencia no puede superar ${OPENING_REFERENCE_MAX_LENGTH} caracteres.`
      : required[field];
  }

  /** Nombres de los productos de las líneas que ya tienen movimientos (para el aviso sobre la tabla). */
  get historyNames(): string[] {
    return this.lines.controls
      .map((_, i) => this.productAt(i))
      .filter((product): product is OpeningProduct => !!product && this.historyIds.has(product.id))
      .map((product) => product.name);
  }

  get canReview(): boolean {
    const valid = this.lines.controls.every((group, i) => {
      const product = group.controls.product.value;
      return !!product && quantityError(group.controls.quantity.value, product.unit.allowsFractions) === null
        && !this.isDuplicate(i);
    });
    return this.form.valid && valid && this.historyNames.length === 0 && !this.checking && !this.saving;
  }

  get warehouseName(): string {
    return this.warehouses.find((w) => w.id === this.form.controls.warehouseId.value)?.name ?? '';
  }

  get summaryLines(): SummaryLine[] {
    return this.lines.controls.map((group) => {
      const product = group.controls.product.value;
      return {
        name: product?.name ?? '',
        quantity: formatQuantity(Number(group.controls.quantity.value).toFixed(3)),
        unit: product?.unit.abbreviation ?? '',
      };
    });
  }

  get hasZeroLines(): boolean {
    return this.lines.controls.some((group) => Number(group.controls.quantity.value) === 0);
  }

  review(): void {
    this.form.markAllAsTouched();
    this.lines.controls.forEach((group) => group.controls.quantity.markAsTouched());
    if (!this.canReview) {
      return;
    }
    this.step = 'review';
  }

  backToEdit(): void {
    this.step = 'edit';
  }

  confirm(): void {
    // Un segundo clic (o Enter) mientras la petición sigue en curso no envía nada.
    if (this.saving || !this.canReview) {
      return;
    }
    this.saving = true;
    this.stockApi
      .register(this.buildInput())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.completed = true;
          this.toastr.success(OPENING_SUCCESS_MESSAGE);
          if (this.returnLink) {
            this.router.navigate(this.returnLink);
          } else {
            this.router.navigate(['/pocketbiz/inventory/stock'], { queryParams: { warehouse_id: result.warehouseId } });
          }
        },
        error: (err: InventoryApiError) => {
          this.saving = false;
          this.showServerError(err);
        },
      });
  }

  private buildInput(): OpeningInput {
    const value = this.form.getRawValue();
    return {
      openingId: this.openingId,
      warehouseId: value.warehouseId,
      movementDate: value.movementDate,
      reference: value.reference.trim(),
      lines: value.lines.map((line) => ({
        productId: line.product?.id ?? '',
        quantity: line.quantity.trim(),
      })),
    };
  }

  private showServerError(err: InventoryApiError): void {
    this.step = 'edit';
    if (err.status === 409 && err.code === 'stock_history_exists') {
      this.historyIds = new Set(err.historyProductIds);
      this.conflictMessage = '';
      return;
    }
    if (err.status === 400) {
      const header: Partial<Record<HeaderField, string>> = {};
      for (const field of ['warehouseId', 'movementDate', 'reference'] as const) {
        const messages = err.fieldErrors[field];
        if (messages?.length) {
          header[field] = messages.join(' ');
        }
      }
      this.serverErrors = header;
      this.serverLineErrors = err.lineErrors;
      this.conflictMessage = err.fieldErrors['nonFieldErrors']?.join(' ') ?? '';
      if (!Object.keys(header).length && !err.lineErrors.some((line) => Object.keys(line).length)) {
        this.conflictMessage = err.message;
      }
      return;
    }
    this.conflictMessage = err.message;
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
        this.baseOptions = products;
        this.productsLoading = false;
        const match = this.preselectedProductId ? products.find((p) => p.id === this.preselectedProductId) : undefined;
        const first = this.lines.at(0);
        if (match && first && !first.controls.product.value) {
          this.preselectedProductId = null;
          first.controls.product.setValue(match);
          this.form.markAsPristine();
          this.onProductsChanged();
        }
        this.refreshOptions();
      });
  }

  private watchHistory(): void {
    this.check$
      .pipe(
        startWith(undefined),
        tap(() => (this.checking = true)),
        switchMap(() => {
          const warehouseId = this.form.controls.warehouseId.value;
          const ids = this.lines.controls.map((_, i) => this.productAt(i)?.id).filter((id): id is string => !!id);
          if (!warehouseId || !ids.length) {
            return of([] as string[]);
          }
          // Si falla, el servidor vuelve a validar al confirmar.
          return this.stockApi.productsWithHistory(warehouseId, ids).pipe(catchError(() => of([] as string[])));
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((ids) => {
        this.historyIds = new Set(ids);
        this.checking = false;
      });
  }

  /** Las opciones ya elegidas en otra línea aparecen deshabilitadas: no se puede repetir un producto. */
  private refreshOptions(): void {
    const chosen = new Set(
      this.lines.controls.map((_, i) => this.productAt(i)?.id).filter((id): id is string => !!id),
    );
    this.productOptions = this.baseOptions.map((option) => ({ ...option, disabled: chosen.has(option.id) }));
  }
}
