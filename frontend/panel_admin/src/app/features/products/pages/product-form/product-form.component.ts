import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { ModulesService } from '../../../../core/service/modules.service';
import { UnitsApiService } from '../../../inventory';
import { PRODUCT_CATEGORIES, Product, ProductApiError, ProductCategory, ProductInput } from '../../models/product';
import { ProductsApiService } from '../../services/products-api.service';

export const NAME_MAX_LENGTH = 150;
/** Hasta 10 enteros y 2 decimales (punto o coma), igual que el límite del servidor. */
const PRICE_PATTERN = /^\d{1,10}([.,]\d{1,2})?$/;

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

export type FormField = keyof ProductInput;

/** Unidad ofrecida en el selector (la actual del producto aunque esté inactiva). */
export interface UnitOption {
  id: string;
  label: string;
}

@Component({
  selector: 'app-product-form',
  templateUrl: './product-form.component.html',
  imports: [ReactiveFormsModule, RouterLink],
})
export class ProductFormComponent implements OnInit {
  readonly nameMaxLength = NAME_MAX_LENGTH;
  readonly categories = PRODUCT_CATEGORIES;
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [notBlank, Validators.maxLength(NAME_MAX_LENGTH)]],
    description: [''],
    category: ['', Validators.required],
    canBuy: [false],
    canSell: [true],
    salePrice: ['', [Validators.required, Validators.pattern(PRICE_PATTERN)]],
    tracksStock: [false],
    baseUnitId: [''],
  });

  productId: string | null = null;
  /** Producto migrado sin categoría: se avisa para que lo clasifique. */
  needsReview = false;
  saving = false;
  loading = false;
  /** Errores de validación devueltos por el servidor, por campo; se limpian al editar. */
  serverErrors: Partial<Record<FormField, string>> = {};
  /** Los datos de inventario solo existen en el formulario con Inventario habilitado. */
  inventoryEnabled = false;
  unitOptions: UnitOption[] = [];
  /** Mensaje de bloqueo por historial de movimientos (409). */
  lockedMessage = '';

  private modules = inject(ModulesService);
  private units = inject(UnitsApiService);
  private api = inject(ProductsApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  get isEdit(): boolean {
    return this.productId !== null;
  }

  ngOnInit(): void {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.serverErrors = {};
      this.lockedMessage = '';
    });
    this.form.controls.canSell.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((sells) => {
      const price = this.form.controls.salePrice;
      // Oculto y sin venta, el precio no debe bloquear el guardado (REV-02).
      price.setValidators(sells ? [Validators.required, Validators.pattern(PRICE_PATTERN)] : []);
      price.updateValueAndValidity({ emitEvent: false });
    });
    this.form.controls.tracksStock.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((tracks) => {
      const unit = this.form.controls.baseUnitId;
      if (tracks) {
        unit.addValidators(Validators.required);
      } else {
        unit.removeValidators(Validators.required);
        unit.setValue('', { emitEvent: false });
      }
      unit.updateValueAndValidity({ emitEvent: false });
    });
    this.modules.enabledKeys$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((keys) => {
      const enabled = keys?.has('inventory') ?? false;
      if (enabled && !this.inventoryEnabled) {
        this.loadUnits();
      }
      this.inventoryEnabled = enabled;
    });
    this.productId = this.route.snapshot.paramMap.get('id');
    if (this.productId) {
      this.loading = true;
      this.api
        .get(this.productId)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (product) => this.fill(product),
          error: (err: ProductApiError) => {
            this.loading = false;
            this.toastr.error(err.message);
            this.router.navigate(['/pocketbiz/catalog/products']);
          },
        });
    }
  }

  hasError(field: FormField): boolean {
    const control = this.form.controls[field];
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverErrors[field];
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const input: ProductInput = {
      name: value.name.trim(),
      description: value.description.trim(),
      // Un producto que no se vende conserva el precio que ya tenía; sin precio se envía null.
      salePrice: this.priceToSend(value.salePrice, value.canSell),
      category: value.category as ProductCategory,
      canBuy: value.canBuy,
      canSell: value.canSell,
    };
    if (this.inventoryEnabled) {
      input.tracksStock = value.tracksStock;
      input.baseUnitId = value.tracksStock ? value.baseUnitId : null;
    }
    this.saving = true;
    const request = this.productId ? this.api.update(this.productId, input) : this.api.create(input);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (product) => {
        this.saving = false;
        this.toastr.success(this.isEdit ? 'Producto actualizado' : 'Producto creado');
        this.router.navigate(this.isEdit ? ['/pocketbiz/catalog/products', product.id] : ['/pocketbiz/catalog/products']);
      },
      error: (err: ProductApiError) => {
        this.saving = false;
        this.showServerError(err);
      },
    });
  }

  private priceToSend(raw: string, sells: boolean): string | null {
    const price = raw.trim();
    if (!price || (!sells && !PRICE_PATTERN.test(price))) {
      return null;
    }
    return price.replace(',', '.');
  }

  private fill(product: Product): void {
    this.form.setValue({
      name: product.name,
      description: product.description,
      category: product.category ?? '',
      canBuy: product.canBuy,
      canSell: product.canSell,
      salePrice: product.salePrice ?? '',
      tracksStock: product.tracksStock,
      baseUnitId: product.baseUnit?.id ?? '',
    });
    this.needsReview = product.needsReview;
    this.currentUnit = product.baseUnit;
    this.addCurrentUnit();
    this.serverErrors = {};
    this.loading = false;
  }

  private currentUnit: { id: string; name: string; abbreviation: string } | null = null;

  private loadUnits(): void {
    this.units
      .list({ active: true, pageSize: 100 })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (page) => {
          this.unitOptions = page.results.map((u) => ({ id: u.id, label: `${u.name} (${u.abbreviation})` }));
          this.addCurrentUnit();
        },
        error: (err: { message: string }) => this.toastr.error(err.message),
      });
  }

  /** El producto conserva su unidad actual aunque se haya desactivado después. */
  private addCurrentUnit(): void {
    const unit = this.currentUnit;
    if (unit && !this.unitOptions.some((o) => o.id === unit.id)) {
      this.unitOptions = [...this.unitOptions, { id: unit.id, label: `${unit.name} (${unit.abbreviation})` }];
    }
  }

  private showServerError(err: ProductApiError): void {
    if (err.code === 'stock_history_locked') {
      this.lockedMessage = err.message;
      return;
    }
    const errors: Partial<Record<FormField, string>> = {};
    for (const field of ['name', 'description', 'category', 'canBuy', 'canSell', 'salePrice', 'tracksStock', 'baseUnitId'] as const) {
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
