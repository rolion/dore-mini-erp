import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { InventoryApiError } from '../../models/api-error';
import { WAREHOUSE_NAME_MAX_LENGTH, Warehouse } from '../../models/warehouse';
import { WarehousesApiService } from '../../services/warehouses-api.service';

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

export type WarehouseField = 'name' | 'description' | 'isDefault';

/** Alta y edición de un almacén en un diálogo; se cierra devolviendo el almacén guardado. */
@Component({
  selector: 'app-warehouse-dialog',
  templateUrl: './warehouse-dialog.component.html',
  imports: [ReactiveFormsModule],
})
export class WarehouseDialogComponent {
  readonly nameMaxLength = WAREHOUSE_NAME_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [notBlank, Validators.maxLength(WAREHOUSE_NAME_MAX_LENGTH)]],
    description: [''],
    isDefault: [false],
  });

  /** Almacén que se edita; `null` para crear. Lo fija quien abre el diálogo. */
  warehouse: Warehouse | null = null;
  saving = false;
  serverErrors: Partial<Record<WarehouseField, string>> = {};

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(WarehousesApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => (this.serverErrors = {}));
  }

  get isEdit(): boolean {
    return this.warehouse !== null;
  }

  /** El almacén predeterminado no se desmarca aquí: se designa otro como predeterminado. */
  get defaultLocked(): boolean {
    return this.warehouse?.isDefault ?? false;
  }

  /** Solo un almacén activo puede ser el predeterminado. */
  get canBeDefault(): boolean {
    return this.warehouse?.active ?? true;
  }

  edit(warehouse: Warehouse): void {
    this.warehouse = warehouse;
    this.form.setValue({ name: warehouse.name, description: warehouse.description, isDefault: warehouse.isDefault });
    if (warehouse.isDefault || !warehouse.active) {
      this.form.controls.isDefault.disable({ emitEvent: false });
    }
  }

  hasError(field: WarehouseField): boolean {
    const control = this.form.controls[field];
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverErrors[field];
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const input = { name: value.name.trim(), description: value.description.trim(), isDefault: value.isDefault };
    this.saving = true;
    const request = this.warehouse ? this.api.update(this.warehouse.id, input) : this.api.create(input);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (saved) => {
        this.saving = false;
        this.toastr.success(this.isEdit ? 'Almacén actualizado' : 'Almacén creado');
        this.activeModal.close(saved);
      },
      error: (err: InventoryApiError) => {
        this.saving = false;
        const errors: Partial<Record<WarehouseField, string>> = {};
        for (const field of ['name', 'description', 'isDefault'] as const) {
          const messages = err.fieldErrors[field];
          if (messages?.length) {
            errors[field] = messages.join(' ');
          }
        }
        this.serverErrors = errors;
        if (!Object.keys(errors).length) {
          this.toastr.error(err.message);
        }
      },
    });
  }
}
