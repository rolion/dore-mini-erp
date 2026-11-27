import { Component, inject } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { CrmTask } from '../../models/task';

export type TaskConfirmAction = 'cancel' | 'archive';

/**
 * Confirmación de cancelar o archivar una tarea (patrón de acción irreversible, sin motivo). Se cierra con `true`
 * al confirmar; cancelar o archivar sigue ocurriendo en la página (el diálogo no llama a la API).
 */
@Component({
  selector: 'app-crm-confirm-task-action-dialog',
  templateUrl: './confirm-task-action-dialog.component.html',
  imports: [TranslatePipe],
})
export class ConfirmTaskActionDialogComponent {
  action: TaskConfirmAction = 'cancel';
  task!: CrmTask;
  readonly activeModal = inject(NgbActiveModal);

  open(action: TaskConfirmAction, task: CrmTask): void {
    this.action = action;
    this.task = task;
  }

  get keyPrefix(): string {
    return this.action === 'archive' ? 'CRM.CONFIRM_TASK.ARCHIVAR' : 'CRM.CONFIRM_TASK.CANCELAR';
  }
}
