import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { CrmApiError, CrmFieldErrors } from '../../models/board';
import { CrmTask } from '../../models/task';
import { CrmTaskCompletion, CrmTasksApiService } from '../../services/crm-tasks-api.service';
import {
  ActivityFieldsComponent, activityFormValid, activityFormValue, createActivityForm,
} from '../activity-fields/activity-fields.component';

/** Completa una tarea y, si la persona lo pide, registra la actividad en el mismo paso. */
@Component({
  selector: 'app-crm-complete-task-dialog',
  templateUrl: './complete-task-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, ActivityFieldsComponent],
})
export class CompleteTaskDialogComponent {
  readonly withActivity = new FormControl(false, { nonNullable: true });
  readonly form = createActivityForm();
  task!: CrmTask;
  saving = false;
  errorMessage = '';
  conflict = false;
  fieldErrors: CrmFieldErrors = {};

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(CrmTasksApiService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.fieldErrors = {};
      this.errorMessage = '';
    });
  }

  open(task: CrmTask): void {
    this.task = task;
  }

  get canConfirm(): boolean {
    return !this.saving && (!this.withActivity.value || activityFormValid(this.form));
  }

  confirm(): void {
    if (!this.canConfirm) return;
    this.saving = true;
    this.errorMessage = '';
    const activity = this.withActivity.value ? activityFormValue(this.form) : undefined;
    this.api.complete(this.task.id, activity).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result: CrmTaskCompletion) => {
        this.saving = false;
        this.activeModal.close(result);
      },
      error: (err: CrmApiError) => {
        this.saving = false;
        this.fieldErrors = err.fieldErrors;
        this.conflict = err.status === 409;
        this.errorMessage = Object.keys(err.fieldErrors).length ? '' : err.message;
      },
    });
  }
}
