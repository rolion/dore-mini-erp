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

/** Alta o renombrado de un tablero; se cierra devolviendo el tablero guardado. */
@Component({
  selector: 'app-crm-board-name-dialog',
  templateUrl: './board-name-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule],
})
export class BoardNameDialogComponent {
  readonly nameMaxLength = CRM_NAME_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [notBlank, Validators.maxLength(CRM_NAME_MAX_LENGTH)]],
  });

  /** Tablero que se renombra; `null` para crear. Lo fija quien abre el diálogo. */
  board: CrmBoard | null = null;
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

  edit(board: CrmBoard): void {
    this.board = board;
    this.form.setValue({ name: board.name });
  }

  get isEdit(): boolean {
    return this.board !== null;
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
    const name = this.form.controls.name.value.trim();
    this.saving = true;
    const request = this.board ? this.api.rename(this.board.id, name) : this.api.create(name);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (saved) => {
        this.saving = false;
        this.activeModal.close(saved);
      },
      error: (err: CrmApiError) => {
        this.saving = false;
        this.serverError = err.fieldErrors.name ?? '';
        this.errorMessage = this.serverError ? '' : err.message;
      },
    });
  }
}
