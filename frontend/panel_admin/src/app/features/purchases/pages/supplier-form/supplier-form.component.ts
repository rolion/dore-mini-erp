import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { Supplier, SupplierApiError, SupplierInput } from '../../models/supplier';
import { SuppliersApiService } from '../../services/suppliers-api.service';

export const NAME_MAX_LENGTH = 150;
export const TAX_ID_MAX_LENGTH = 50;
export const PHONE_MAX_LENGTH = 30;
export const EMAIL_MAX_LENGTH = 254;
export const NOTES_MAX_LENGTH = 2000;
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

/** El correo es opcional; se valida recortado porque el valor enviado también se recorta. */
function emailFormat(control: AbstractControl<string>): ValidationErrors | null {
  const value = control.value.trim();
  return !value || EMAIL_PATTERN.test(value) ? null : { pattern: true };
}

export type FormField = keyof SupplierInput;

const FORM_FIELDS: readonly FormField[] = ['name', 'taxId', 'phone', 'email', 'notes'];

@Component({
  selector: 'app-supplier-form',
  templateUrl: './supplier-form.component.html',
  imports: [ReactiveFormsModule, RouterLink],
})
export class SupplierFormComponent implements OnInit {
  readonly nameMaxLength = NAME_MAX_LENGTH;
  readonly taxIdMaxLength = TAX_ID_MAX_LENGTH;
  readonly phoneMaxLength = PHONE_MAX_LENGTH;
  readonly emailMaxLength = EMAIL_MAX_LENGTH;
  readonly notesMaxLength = NOTES_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [notBlank, Validators.maxLength(NAME_MAX_LENGTH)]],
    taxId: ['', [Validators.maxLength(TAX_ID_MAX_LENGTH)]],
    phone: ['', [Validators.maxLength(PHONE_MAX_LENGTH)]],
    email: ['', [emailFormat, Validators.maxLength(EMAIL_MAX_LENGTH)]],
    notes: ['', [Validators.maxLength(NOTES_MAX_LENGTH)]],
  });

  supplierId: string | null = null;
  saving = false;
  loading = false;
  /** Errores de validación devueltos por el servidor, por campo; se limpian al editar. */
  serverErrors: Partial<Record<FormField, string>> = {};

  private api = inject(SuppliersApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  get isEdit(): boolean {
    return this.supplierId !== null;
  }

  ngOnInit(): void {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => (this.serverErrors = {}));
    this.supplierId = this.route.snapshot.paramMap.get('id');
    if (this.supplierId) {
      this.loading = true;
      this.api
        .get(this.supplierId)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (supplier) => this.fill(supplier),
          error: (err: SupplierApiError) => {
            this.loading = false;
            this.toastr.error(err.message);
            this.router.navigate(['/pocketbiz/purchases/suppliers']);
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
    const input: SupplierInput = {
      name: value.name.trim(),
      taxId: value.taxId.trim(),
      phone: value.phone.trim(),
      email: value.email.trim(),
      notes: value.notes.trim(),
    };
    this.saving = true;
    const request = this.supplierId ? this.api.update(this.supplierId, input) : this.api.create(input);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (supplier) => {
        this.saving = false;
        this.toastr.success(this.isEdit ? 'Proveedor actualizado' : 'Proveedor creado');
        this.router.navigate(['/pocketbiz/purchases/suppliers', supplier.id]);
      },
      error: (err: SupplierApiError) => {
        this.saving = false;
        this.showServerError(err);
      },
    });
  }

  private fill(supplier: Supplier): void {
    this.form.setValue({
      name: supplier.name,
      taxId: supplier.taxId,
      phone: supplier.phone,
      email: supplier.email,
      notes: supplier.notes,
    });
    this.serverErrors = {};
    this.loading = false;
  }

  private showServerError(err: SupplierApiError): void {
    const errors: Partial<Record<FormField, string>> = {};
    for (const field of FORM_FIELDS) {
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
