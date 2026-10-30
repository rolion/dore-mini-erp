import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { Supplier, SupplierApiError, SupplierInput } from '../../models/supplier';
import { SuppliersApiService } from '../../services/suppliers-api.service';

export const NAME_MAX_LENGTH = 150;
export const TAX_ID_MAX_LENGTH = 50;
export const PHONE_MAX_LENGTH = 30;
export const EMAIL_MAX_LENGTH = 254;
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

type QuickField = 'name' | 'taxId' | 'phone' | 'email';
const FIELDS: readonly QuickField[] = ['name', 'taxId', 'phone', 'email'];

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

function emailFormat(control: AbstractControl<string>): ValidationErrors | null {
  const value = control.value.trim();
  return !value || EMAIL_PATTERN.test(value) ? null : { pattern: true };
}

/**
 * Contenido del modal de creación rápida de proveedor que se abre desde el formulario de compra. Usa la misma API
 * que el formulario de proveedores; al guardar cierra el modal devolviendo el proveedor creado.
 */
@Component({
  selector: 'app-supplier-quick-create',
  templateUrl: './supplier-quick-create.component.html',
  imports: [ReactiveFormsModule],
})
export class SupplierQuickCreateComponent {
  readonly activeModal = inject(NgbActiveModal);
  readonly nameMaxLength = NAME_MAX_LENGTH;
  readonly taxIdMaxLength = TAX_ID_MAX_LENGTH;
  readonly phoneMaxLength = PHONE_MAX_LENGTH;
  readonly emailMaxLength = EMAIL_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [notBlank, Validators.maxLength(NAME_MAX_LENGTH)]],
    taxId: ['', [Validators.maxLength(TAX_ID_MAX_LENGTH)]],
    phone: ['', [Validators.maxLength(PHONE_MAX_LENGTH)]],
    email: ['', [emailFormat, Validators.maxLength(EMAIL_MAX_LENGTH)]],
  });

  saving = false;
  /** Errores de validación del servidor por campo. */
  serverErrors: Partial<Record<QuickField, string>> = {};

  private api = inject(SuppliersApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  hasError(field: QuickField): boolean {
    const control = this.form.controls[field];
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverErrors[field];
  }

  submit(): void {
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
      notes: '',
    };
    this.saving = true;
    this.serverErrors = {};
    this.api
      .create(input)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (supplier: Supplier) => {
          this.saving = false;
          this.toastr.success('Proveedor creado');
          this.activeModal.close(supplier);
        },
        error: (err: SupplierApiError) => {
          this.saving = false;
          const errors: Partial<Record<QuickField, string>> = {};
          for (const field of FIELDS) {
            const messages = err.fieldErrors[field];
            if (messages?.length) errors[field] = messages.join(' ');
          }
          this.serverErrors = errors;
          if (!Object.keys(errors).length) this.toastr.error(err.message);
        },
      });
  }
}
