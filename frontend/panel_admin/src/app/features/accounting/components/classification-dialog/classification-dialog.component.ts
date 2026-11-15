import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { ToastrService } from 'ngx-toastr';
import { tr } from '../../../../core/i18n/translate';
import { ACCOUNT_NAME_MAX_LENGTH, AccountingApiError, Classification, DIRECTIONS, Direction } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

export type ClassificationField = 'name' | 'direction';

/** Alta y edición de una clasificación; la dirección solo se elige al crear. Cierra devolviendo la guardada. */
@Component({
  selector: 'app-classification-dialog',
  templateUrl: './classification-dialog.component.html',
  styleUrl: './classification-dialog.component.scss',
  imports: [TranslatePipe, ReactiveFormsModule],
})
export class ClassificationDialogComponent {
  readonly nameMaxLength = ACCOUNT_NAME_MAX_LENGTH;
  readonly directions = DIRECTIONS;
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [notBlank, Validators.maxLength(ACCOUNT_NAME_MAX_LENGTH)]],
    direction: ['INCOME' as Direction, Validators.required],
  });

  /** Clasificación que se edita; `null` para crear. Lo fija quien abre el diálogo. */
  classification: Classification | null = null;
  saving = false;
  serverErrors: Partial<Record<ClassificationField, string>> = {};

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(AccountingApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => (this.serverErrors = {}));
  }

  get isEdit(): boolean {
    return this.classification !== null;
  }

  edit(classification: Classification): void {
    this.classification = classification;
    this.form.setValue({ name: classification.name, direction: classification.direction });
    this.form.controls.direction.disable();
  }

  hasError(field: ClassificationField): boolean {
    const control = this.form.controls[field];
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverErrors[field];
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const name = value.name.trim();
    this.saving = true;
    const request = this.classification
      ? this.api.renameClassification(this.classification.id, name)
      : this.api.createClassification({ name, direction: value.direction });
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (saved) => {
        this.saving = false;
        this.toastr.success(this.isEdit ? tr('ACCOUNTING.CLASSIFICATIONS.CLASIFICACION_ACTUALIZADA') : tr('ACCOUNTING.CLASSIFICATIONS.CLASIFICACION_CREADA'));
        this.activeModal.close(saved);
      },
      error: (err: AccountingApiError) => {
        this.saving = false;
        const errors: Partial<Record<ClassificationField, string>> = {};
        for (const field of ['name', 'direction'] as const) {
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
