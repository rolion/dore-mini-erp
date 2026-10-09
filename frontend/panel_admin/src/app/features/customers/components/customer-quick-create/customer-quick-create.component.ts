import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import Swal from 'sweetalert2';
import { Customer, CustomerApiError, DuplicateCustomerError, DuplicateMatch } from '../../models/customer';
import { duplicateMatchesHtml, NAME_MAX_LENGTH, PHONE_MAX_LENGTH } from '../../pages/customer-form/customer-form.component';
import { CustomersApiService } from '../../services/customers-api.service';

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

/**
 * Contenido del modal de creación rápida de cliente (nombre y teléfono) que se abre desde un pedido. Reutiliza la
 * misma API y el mismo diálogo de duplicado que el formulario de clientes; al guardar cierra el modal devolviendo
 * el cliente creado.
 */
@Component({
  selector: 'app-customer-quick-create',
  templateUrl: './customer-quick-create.component.html',
  imports: [ReactiveFormsModule],
})
export class CustomerQuickCreateComponent {
  readonly activeModal = inject(NgbActiveModal);
  readonly nameMaxLength = NAME_MAX_LENGTH;
  readonly phoneMaxLength = PHONE_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [notBlank, Validators.maxLength(NAME_MAX_LENGTH)]],
    phone: ['', [Validators.maxLength(PHONE_MAX_LENGTH)]],
  });

  saving = false;
  /** Errores de validación del servidor por campo. */
  serverErrors: Partial<Record<'name' | 'phone', string>> = {};

  private api = inject(CustomersApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  submit(): void {
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
    this.saving = true;
    this.serverErrors = {};
    this.api
      .create({ name: value.name.trim(), phone: value.phone.trim(), email: '', notes: '' }, confirmDuplicate)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (customer: Customer) => {
          this.saving = false;
          this.toastr.success('Cliente creado');
          this.activeModal.close(customer);
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

  private showServerError(err: CustomerApiError): void {
    const errors: Partial<Record<'name' | 'phone', string>> = {};
    for (const field of ['name', 'phone'] as const) {
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
