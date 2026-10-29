import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  FormArray,
  FormBuilder,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgFooterTemplateDirective, NgSelectComponent } from '@ng-select/ng-select';
import { ToastrService } from 'ngx-toastr';
import { Observable, Subject, catchError, debounceTime, defer, distinctUntilChanged, map, of, switchMap } from 'rxjs';
import { HasUnsavedChanges } from '../../../../core/guard/unsaved-changes.guard';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { Product, ProductsApiService } from '../../../products';
import {
  HeaderField,
  ItemErrors,
  MAX_ITEMS,
  NOTES_MAX_LENGTH,
  PURCHASE_CURRENCY,
  Purchase,
  PurchaseApiError,
  PurchaseInput,
  PurchaseSupplier,
  REFERENCE_MAX_LENGTH,
  todayIso,
} from '../../models/purchase';
import { Supplier } from '../../models/supplier';
import { PurchasesApiService } from '../../services/purchases-api.service';
import { isValidPrice, isValidQuantity, lineSubtotal, purchaseTotal } from '../../services/purchase-amounts';
import { SupplierQuickCreateService } from '../../services/supplier-quick-create.service';
import { SuppliersApiService } from '../../services/suppliers-api.service';

export const SEARCH_PAGE_SIZE = 20;
export const NOT_EDITABLE_MESSAGE = 'La compra ya no admite cambios.';

/** Producto elegido en una línea: lo mínimo que la pantalla necesita mostrar y validar. */
export interface LineProduct {
  id: string;
  name: string;
  /** Abreviatura de la unidad base; vacía si el producto no tiene. */
  unit: string;
  allowsFractions: boolean;
}

function toLineProduct(product: Product): LineProduct {
  const unit = product.baseUnit;
  return {
    id: product.id,
    name: product.name,
    unit: unit?.abbreviation ?? '',
    allowsFractions: unit ? (unit.allowsFractions ?? true) : true,
  };
}

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

function quantityRule(control: AbstractControl<string>): ValidationErrors | null {
  const product = control.parent?.get('product')?.value as LineProduct | null | undefined;
  return isValidQuantity(control.value, product?.allowsFractions ?? true) ? null : { quantity: true };
}

function priceRule(control: AbstractControl<string>): ValidationErrors | null {
  return isValidPrice(control.value) ? null : { price: true };
}

export type LineGroup = FormGroup<{
  product: FormControl<LineProduct | null>;
  quantity: FormControl<string>;
  unitPrice: FormControl<string>;
}>;

/** Formulario único de la compra en borrador: cabecera y líneas. Los importes mostrados son solo informativos. */
@Component({
  selector: 'app-purchase-form',
  templateUrl: './purchase-form.component.html',
  imports: [ReactiveFormsModule, RouterLink, NgSelectComponent, NgFooterTemplateDirective, MoneyPipe],
})
export class PurchaseFormComponent implements OnInit, HasUnsavedChanges {
  readonly currency = PURCHASE_CURRENCY;
  readonly maxItems = MAX_ITEMS;
  readonly referenceMaxLength = REFERENCE_MAX_LENGTH;
  readonly notesMaxLength = NOTES_MAX_LENGTH;

  private fb = inject(FormBuilder).nonNullable;
  readonly form = this.fb.group({
    supplier: [null as PurchaseSupplier | null, Validators.required],
    purchaseDate: [todayIso(), Validators.required],
    externalReference: ['', Validators.maxLength(REFERENCE_MAX_LENGTH)],
    notes: ['', Validators.maxLength(NOTES_MAX_LENGTH)],
    items: this.fb.array<LineGroup>([]),
  });

  purchaseId: string | null = null;
  saving = false;
  loading = false;
  /** Proveedor del borrador desactivado después de guardarlo: hay que elegir otro. */
  supplierInactive = false;
  /** Errores del servidor; se limpian al editar. */
  serverHeader: Partial<Record<HeaderField, string>> = {};
  serverItems: ItemErrors[] = [];
  serverItemsMessage = '';
  generalError = '';

  readonly supplierInput$ = new Subject<string>();
  supplierOptions: PurchaseSupplier[] = [];
  suppliersLoading = false;
  /** Sin proveedores activos en la empresa (búsqueda vacía sin resultados). */
  noSuppliers = false;

  readonly productInput$ = new Subject<string>();
  productOptions: LineProduct[] = [];
  productsLoading = false;
  /** Opciones por línea: sin los productos ya elegidos en otras líneas. */
  lineOptions: LineProduct[][] = [];

  private purchasesApi = inject(PurchasesApiService);
  private suppliersApi = inject(SuppliersApiService);
  private productsApi = inject(ProductsApiService);
  private quickCreate = inject(SupplierQuickCreateService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);
  private saved = false;

  get items(): FormArray<LineGroup> {
    return this.form.controls.items;
  }

  get isEdit(): boolean {
    return this.purchaseId !== null;
  }

  get itemRows(): readonly LineGroup[] {
    return this.items.controls;
  }

  hasUnsavedChanges(): boolean {
    return this.form.dirty && !this.saved;
  }

  ngOnInit(): void {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.serverHeader = {};
      this.serverItems = [];
      this.serverItemsMessage = '';
      this.generalError = '';
      this.refreshLineOptions();
    });
    this.watchSuppliers();
    this.watchProducts();
    this.purchaseId = this.route.snapshot.paramMap.get('id');
    if (this.purchaseId) {
      this.loading = true;
      this.purchasesApi
        .get(this.purchaseId)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (purchase) => this.fill(purchase),
          error: (err: PurchaseApiError) => {
            this.loading = false;
            this.toastr.error(err.message);
            void this.router.navigate(['/pocketbiz/purchases']);
          },
        });
    }
  }

  // --- líneas ---------------------------------------------------------------------------------------------------

  addLine(product: LineProduct | null = null, quantity = '', unitPrice = ''): void {
    if (this.items.length >= MAX_ITEMS) return;
    this.items.push(
      this.fb.group({
        product: [product, Validators.required],
        quantity: [quantity, [notBlank, quantityRule]],
        unitPrice: [unitPrice, [notBlank, priceRule]],
      }),
    );
    this.items.markAsDirty();
  }

  removeLine(index: number): void {
    this.items.removeAt(index);
    this.items.markAsDirty();
  }

  /** Al cambiar de producto se revalida la cantidad (la unidad puede no admitir fracciones). */
  onProductChange(line: LineGroup): void {
    line.controls.quantity.updateValueAndValidity();
  }

  unit(line: LineGroup): string {
    return line.controls.product.value?.unit || '—';
  }

  subtotal(line: LineGroup): string | null {
    return lineSubtotal(line.controls.quantity.value, line.controls.unitPrice.value);
  }

  total(): string {
    return purchaseTotal(
      this.items.controls.map((line) => ({
        quantity: line.controls.quantity.value,
        unitPrice: line.controls.unitPrice.value,
      })),
    );
  }

  /** Mensaje de un campo de la línea: el del servidor, o el de la validación local una vez tocado. */
  lineError(index: number, field: 'productId' | 'quantity' | 'unitPrice'): string {
    const server = this.serverItems[index]?.[field];
    if (server) return server;
    const line = this.items.at(index);
    const control = line.controls[field === 'productId' ? 'product' : field];
    if (!(control.invalid && (control.touched || control.dirty))) return '';
    switch (field) {
      case 'productId':
        return 'Selecciona un producto.';
      case 'quantity': {
        const allows = line.controls.product.value?.allowsFractions ?? true;
        return allows
          ? 'La cantidad debe ser mayor a cero (hasta 3 decimales).'
          : 'La cantidad debe ser un entero mayor a cero.';
      }
      case 'unitPrice':
        return 'El precio debe ser cero o mayor (hasta 2 decimales).';
    }
  }

  // --- cabecera -------------------------------------------------------------------------------------------------

  headerError(field: HeaderField): string {
    if (this.serverHeader[field]) return this.serverHeader[field] ?? '';
    const control = this.form.controls[field === 'supplierId' ? 'supplier' : field];
    if (!(control.invalid && (control.touched || control.dirty))) return '';
    const messages: Record<HeaderField, string> = {
      supplierId: 'Selecciona un proveedor activo.',
      purchaseDate: 'La fecha de compra es obligatoria.',
      externalReference: `La referencia no puede superar ${REFERENCE_MAX_LENGTH} caracteres.`,
      notes: `Las notas no pueden superar ${NOTES_MAX_LENGTH} caracteres.`,
    };
    return messages[field];
  }

  /** Crea un proveedor sin salir de la pantalla (modal) y lo deja seleccionado; lo escrito se conserva. */
  async createSupplier(): Promise<void> {
    const supplier = await this.quickCreate.open();
    if (supplier) {
      this.selectSupplier(supplier);
    }
  }

  selectSupplier(supplier: Supplier): void {
    const option: PurchaseSupplier = { id: supplier.id, name: supplier.name };
    this.supplierOptions = [option, ...this.supplierOptions.filter((o) => o.id !== option.id)];
    this.noSuppliers = false;
    this.supplierInactive = false;
    this.form.controls.supplier.setValue(option);
    this.form.controls.supplier.markAsDirty();
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving || this.loading) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const input: PurchaseInput = {
      supplierId: value.supplier?.id ?? '',
      purchaseDate: value.purchaseDate,
      externalReference: value.externalReference.trim(),
      notes: value.notes.trim(),
      items: this.items.controls.map((line) => ({
        productId: line.controls.product.value?.id ?? '',
        quantity: line.controls.quantity.value.trim(),
        unitPrice: line.controls.unitPrice.value.trim(),
      })),
    };
    this.saving = true;
    const request = this.purchaseId
      ? this.purchasesApi.update(this.purchaseId, input)
      : this.purchasesApi.create(input);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (purchase) => {
        this.saving = false;
        this.saved = true;
        this.toastr.success('Compra guardada');
        void this.router.navigate(['/pocketbiz/purchases', purchase.id]);
      },
      error: (err: PurchaseApiError) => {
        this.saving = false;
        this.showServerError(err);
      },
    });
  }

  // --- internos -------------------------------------------------------------------------------------------------

  private fill(purchase: Purchase): void {
    if (!purchase.editable) {
      this.toastr.error(NOT_EDITABLE_MESSAGE);
      void this.router.navigate(['/pocketbiz/purchases', purchase.id]);
      return;
    }
    this.supplierInactive = !purchase.supplier.active;
    this.form.patchValue({
      supplier: { id: purchase.supplier.id, name: purchase.supplier.name },
      purchaseDate: purchase.purchaseDate,
      externalReference: purchase.externalReference,
      notes: purchase.notes,
    });
    this.items.clear();
    for (const item of purchase.items) {
      this.addLine(
        { id: item.productId, name: item.productName, unit: item.unitAbbreviation, allowsFractions: true },
        item.quantity,
        item.unitPrice,
      );
    }
    this.form.markAsPristine();
    this.loading = false;
  }

  private showServerError(err: PurchaseApiError): void {
    this.serverHeader = err.fieldErrors.header;
    this.serverItems = err.fieldErrors.items;
    this.serverItemsMessage = err.fieldErrors.itemsMessage ?? '';
    const hasFieldErrors =
      Object.keys(err.fieldErrors.header).length > 0 ||
      err.fieldErrors.items.some((line) => Object.keys(line).length > 0) ||
      !!this.serverItemsMessage;
    if (!hasFieldErrors) {
      this.generalError = err.message;
    }
    if (err.status === 409) {
      this.toastr.error(err.message);
    }
  }

  private refreshLineOptions(): void {
    const chosen = this.items.controls.map((line) => line.controls.product.value?.id);
    this.lineOptions = this.items.controls.map((line, index) =>
      this.productOptions.filter((p) => !chosen.some((id, other) => id === p.id && other !== index)),
    );
  }

  /** Lista inicial de proveedores activos y, luego, búsqueda remota por nombre mientras se escribe. */
  private watchSuppliers(): void {
    this.searchSuppliers('')
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((options) => {
        this.supplierOptions = options;
        this.noSuppliers = options.length === 0;
      });
    this.supplierInput$
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((term: string | null) => {
          this.suppliersLoading = true;
          return this.searchSuppliers(term);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((options) => {
        this.suppliersLoading = false;
        this.supplierOptions = options;
      });
    this.destroyRef.onDestroy(() => this.supplierInput$.complete());
  }

  private watchProducts(): void {
    this.searchProducts('')
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((options) => {
        this.productOptions = options;
        this.refreshLineOptions();
      });
    this.productInput$
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((term: string | null) => {
          this.productsLoading = true;
          return this.searchProducts(term);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((options) => {
        this.productsLoading = false;
        this.productOptions = options;
        this.refreshLineOptions();
      });
    this.destroyRef.onDestroy(() => this.productInput$.complete());
  }

  /** `ng-select` emite `null` por el typeahead al elegir o limpiar; un fallo deja la lista vacía sin romper el stream. */
  private searchSuppliers(term: string | null | undefined): Observable<PurchaseSupplier[]> {
    return defer(() =>
      this.suppliersApi.list({ search: (term ?? '').trim(), active: true, pageSize: SEARCH_PAGE_SIZE }),
    ).pipe(
      map((page) => page.results.map((s) => ({ id: s.id, name: s.name }))),
      catchError(() => of([] as PurchaseSupplier[])),
    );
  }

  private searchProducts(term: string | null | undefined): Observable<LineProduct[]> {
    return defer(() =>
      this.productsApi.list({ search: (term ?? '').trim(), active: true, pageSize: SEARCH_PAGE_SIZE }),
    ).pipe(
      map((page) => page.results.map(toLineProduct)),
      catchError(() => of([] as LineProduct[])),
    );
  }
}
