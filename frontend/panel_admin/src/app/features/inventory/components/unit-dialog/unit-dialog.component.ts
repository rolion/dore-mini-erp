import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { InventoryApiError } from '../../models/api-error';
import { UNIT_ABBREVIATION_MAX_LENGTH, UNIT_NAME_MAX_LENGTH, Unit } from '../../models/unit';
import { UnitsApiService } from '../../services/units-api.service';

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

export type UnitField = 'name' | 'abbreviation';

/** Alta y edición de una unidad de medida en un diálogo; se cierra devolviendo la unidad guardada. */
@Component({
  selector: 'app-unit-dialog',
  templateUrl: './unit-dialog.component.html',
  imports: [ReactiveFormsModule],
})
export class UnitDialogComponent {
  readonly nameMaxLength = UNIT_NAME_MAX_LENGTH;
  readonly abbreviationMaxLength = UNIT_ABBREVIATION_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [notBlank, Validators.maxLength(UNIT_NAME_MAX_LENGTH)]],
    abbreviation: ['', [notBlank, Validators.maxLength(UNIT_ABBREVIATION_MAX_LENGTH)]],
    allowsFractions: [false],
  });

  /** Unidad que se edita; `null` para crear. La fija quien abre el diálogo. */
  unit: Unit | null = null;
  saving = false;
  serverErrors: Partial<Record<UnitField, string>> = {};

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(UnitsApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => (this.serverErrors = {}));
  }

  get isEdit(): boolean {
    return this.unit !== null;
  }

  /** Una unidad asignada a productos conserva su significado: solo se activa o desactiva. */
  get locked(): boolean {
    return this.unit?.inUse ?? false;
  }

  edit(unit: Unit): void {
    this.unit = unit;
    this.form.setValue({ name: unit.name, abbreviation: unit.abbreviation, allowsFractions: unit.allowsFractions });
    if (unit.inUse) {
      this.form.disable({ emitEvent: false });
    }
  }

  hasError(field: UnitField): boolean {
    const control = this.form.controls[field];
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverErrors[field];
  }

  onSubmit(): void {
    if (this.locked) {
      this.activeModal.dismiss();
      return;
    }
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const input = { name: value.name.trim(), abbreviation: value.abbreviation.trim(), allowsFractions: value.allowsFractions };
    this.saving = true;
    const request = this.unit ? this.api.update(this.unit.id, input) : this.api.create(input);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (saved) => {
        this.saving = false;
        this.toastr.success(this.isEdit ? 'Unidad actualizada' : 'Unidad creada');
        this.activeModal.close(saved);
      },
      error: (err: InventoryApiError) => {
        this.saving = false;
        const errors: Partial<Record<UnitField, string>> = {};
        for (const field of ['name', 'abbreviation'] as const) {
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
