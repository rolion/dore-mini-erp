import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { ExpensesApiError } from '../../models/api-error';
import { CATEGORY_NAME_MAX_LENGTH, ExpenseCategory } from '../../models/category';
import { CategoriesApiService } from '../../services/categories-api.service';

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

/**
 * Alta y edición de una categoría en un diálogo. Se abre con `NgbModal` y se cierra devolviendo la categoría
 * guardada; si el usuario cancela, se descarta sin resultado.
 */
@Component({
  selector: 'app-category-dialog',
  templateUrl: './category-dialog.component.html',
  imports: [ReactiveFormsModule],
})
export class CategoryDialogComponent {
  readonly nameMaxLength = CATEGORY_NAME_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [notBlank, Validators.maxLength(CATEGORY_NAME_MAX_LENGTH)]],
  });

  /** Categoría que se edita; `null` para crear. La fija quien abre el diálogo. */
  category: ExpenseCategory | null = null;
  saving = false;
  serverError = '';

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(CategoriesApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => (this.serverError = ''));
  }

  get isEdit(): boolean {
    return this.category !== null;
  }

  /** Fija la categoría a editar y rellena el formulario. */
  edit(category: ExpenseCategory): void {
    this.category = category;
    this.form.setValue({ name: category.name });
  }

  hasError(): boolean {
    const control = this.form.controls.name;
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverError;
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    const name = this.form.getRawValue().name.trim();
    this.saving = true;
    const request = this.category ? this.api.rename(this.category.id, name) : this.api.create(name);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (saved) => {
        this.saving = false;
        this.toastr.success(this.isEdit ? 'Categoría actualizada' : 'Categoría creada');
        this.activeModal.close(saved);
      },
      error: (err: ExpensesApiError) => {
        this.saving = false;
        const messages = err.fieldErrors['name'];
        if (messages?.length) {
          this.serverError = messages.join(' ');
        } else {
          this.toastr.error(err.message);
        }
      },
    });
  }
}
