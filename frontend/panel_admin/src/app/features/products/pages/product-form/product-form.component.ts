import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { Product, ProductApiError, ProductInput } from '../../models/product';
import { ProductsApiService } from '../../services/products-api.service';

export const NAME_MAX_LENGTH = 150;
/** Hasta 10 enteros y 2 decimales (punto o coma), igual que el límite del servidor. */
const PRICE_PATTERN = /^\d{1,10}([.,]\d{1,2})?$/;

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

export type FormField = keyof ProductInput;

@Component({
  selector: 'app-product-form',
  templateUrl: './product-form.component.html',
  imports: [ReactiveFormsModule, RouterLink],
})
export class ProductFormComponent implements OnInit {
  readonly nameMaxLength = NAME_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [notBlank, Validators.maxLength(NAME_MAX_LENGTH)]],
    description: [''],
    salePrice: ['', [Validators.required, Validators.pattern(PRICE_PATTERN)]],
  });

  productId: string | null = null;
  saving = false;
  loading = false;
  /** Errores de validación devueltos por el servidor, por campo; se limpian al editar. */
  serverErrors: Partial<Record<FormField, string>> = {};

  private api = inject(ProductsApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  get isEdit(): boolean {
    return this.productId !== null;
  }

  ngOnInit(): void {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => (this.serverErrors = {}));
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
            this.router.navigate(['/catalog/products']);
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
      salePrice: value.salePrice.replace(',', '.'),
    };
    this.saving = true;
    const request = this.productId ? this.api.update(this.productId, input) : this.api.create(input);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (product) => {
        this.saving = false;
        this.toastr.success(this.isEdit ? 'Producto actualizado' : 'Producto creado');
        this.router.navigate(this.isEdit ? ['/catalog/products', product.id] : ['/catalog/products']);
      },
      error: (err: ProductApiError) => {
        this.saving = false;
        this.showServerError(err);
      },
    });
  }

  private fill(product: Product): void {
    this.form.setValue({ name: product.name, description: product.description, salePrice: product.salePrice });
    this.serverErrors = {};
    this.loading = false;
  }

  private showServerError(err: ProductApiError): void {
    const errors: Partial<Record<FormField, string>> = {};
    for (const field of ['name', 'description', 'salePrice'] as const) {
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
