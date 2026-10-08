import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import Swal from 'sweetalert2';
import {
  Customer,
  CustomerApiError,
  CustomerInput,
  DuplicateCustomerError,
  DuplicateMatch,
} from '../../models/customer';
import { CustomersApiService } from '../../services/customers-api.service';

export const NAME_MAX_LENGTH = 150;
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

export type FormField = keyof CustomerInput;

const HTML_ESCAPES: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

/** Los nombres vienen de datos de usuario: se escapan antes de mostrarlos como HTML en el diálogo. */
export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (char) => HTML_ESCAPES[char]);
}

export function duplicateMatchesHtml(matches: DuplicateMatch[]): string {
  const items = matches
    .map((match) => {
      const state = match.active ? '' : ' <em>(inactivo)</em>';
      const link = `/customers/${encodeURIComponent(match.id)}`;
      return `<li><a href="${link}" target="_blank" rel="noopener">${escapeHtml(match.name)}</a>${state}</li>`;
    })
    .join('');
  return `<p>Estos clientes ya tienen ese teléfono:</p><ul class="text-start">${items}</ul>`;
}

@Component({
  selector: 'app-customer-form',
  templateUrl: './customer-form.component.html',
  imports: [ReactiveFormsModule, RouterLink],
})
export class CustomerFormComponent implements OnInit {
  readonly nameMaxLength = NAME_MAX_LENGTH;
  readonly phoneMaxLength = PHONE_MAX_LENGTH;
  readonly emailMaxLength = EMAIL_MAX_LENGTH;
  readonly notesMaxLength = NOTES_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [notBlank, Validators.maxLength(NAME_MAX_LENGTH)]],
    phone: ['', [Validators.maxLength(PHONE_MAX_LENGTH)]],
    email: ['', [emailFormat, Validators.maxLength(EMAIL_MAX_LENGTH)]],
    notes: ['', [Validators.maxLength(NOTES_MAX_LENGTH)]],
  });

  customerId: string | null = null;
  saving = false;
  loading = false;
  /** Errores de validación devueltos por el servidor, por campo; se limpian al editar. */
  serverErrors: Partial<Record<FormField, string>> = {};

  private api = inject(CustomersApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  get isEdit(): boolean {
    return this.customerId !== null;
  }

  ngOnInit(): void {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => (this.serverErrors = {}));
    this.customerId = this.route.snapshot.paramMap.get('id');
    if (this.customerId) {
      this.loading = true;
      this.api
        .get(this.customerId)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (customer) => this.fill(customer),
          error: (err: CustomerApiError) => {
            this.loading = false;
            this.toastr.error(err.message);
            this.router.navigate(['/customers']);
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
    this.save(false);
  }

  /** Diálogo previo a crear un cliente duplicado; separado para poder sustituirlo en pruebas. */
  protected async confirmDuplicate(matches: DuplicateMatch[]): Promise<boolean> {
    const result = await Swal.fire({
      title: 'Ya existe un cliente con este teléfono',
      html: duplicateMatchesHtml(matches),
      showCancelButton: true,
      confirmButtonColor: '#8963ff',
      cancelButtonColor: '#fb7823',
      confirmButtonText: 'Crear de todos modos',
      cancelButtonText: 'Cancelar',
    });
    return result.isConfirmed;
  }

  private save(confirmDuplicate: boolean): void {
    const value = this.form.getRawValue();
    const input: CustomerInput = {
      name: value.name.trim(),
      phone: value.phone.trim(),
      email: value.email.trim(),
      notes: value.notes.trim(),
    };
    this.saving = true;
    const request = this.customerId
      ? this.api.update(this.customerId, input)
      : this.api.create(input, confirmDuplicate);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (customer) => {
        this.saving = false;
        this.toastr.success(this.isEdit ? 'Cliente actualizado' : 'Cliente creado');
        this.router.navigate(['/customers', customer.id]);
      },
      error: (err: CustomerApiError) => {
        this.saving = false;
        if (err instanceof DuplicateCustomerError) {
          void this.resolveDuplicate(err);
          return;
        }
        this.showServerError(err);
      },
    });
  }

  private async resolveDuplicate(err: DuplicateCustomerError): Promise<void> {
    if (await this.confirmDuplicate(err.matches)) {
      this.save(true);
    }
  }

  private fill(customer: Customer): void {
    this.form.setValue({
      name: customer.name,
      phone: customer.phone,
      email: customer.email,
      notes: customer.notes,
    });
    this.serverErrors = {};
    this.loading = false;
  }

  private showServerError(err: CustomerApiError): void {
    const errors: Partial<Record<FormField, string>> = {};
    for (const field of ['name', 'phone', 'email', 'notes'] as const) {
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
