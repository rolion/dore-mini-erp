import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { CRM_NAME_MAX_LENGTH, CrmApiError, CrmBoard } from '../../models/board';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

/** Alta de una columna (etapa) al final de un tablero; se cierra devolviendo el tablero actualizado. */
@Component({
  selector: 'app-crm-stage-name-dialog',
  templateUrl: './stage-name-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule],
})
export class StageNameDialogComponent {
  readonly nameMaxLength = CRM_NAME_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [notBlank, Validators.maxLength(CRM_NAME_MAX_LENGTH)]],
  });

  /** Tablero al que se agrega la columna. Lo fija quien abre el diálogo. */
  boardId = '';
  saving = false;
  serverError = '';
  errorMessage = '';

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(CrmBoardsApiService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.serverError = '';
      this.errorMessage = '';
    });
  }

  get showError(): boolean {
    const control = this.form.controls.name;
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverError;
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving = true;
    this.api.addStage(this.boardId, this.form.controls.name.value.trim()).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (board: CrmBoard) => {
        this.saving = false;
        this.activeModal.close(board);
      },
      error: (err: CrmApiError) => {
        this.saving = false;
        this.serverError = err.fieldErrors.name ?? '';
        this.errorMessage = this.serverError ? '' : err.message;
      },
    });
  }
}
