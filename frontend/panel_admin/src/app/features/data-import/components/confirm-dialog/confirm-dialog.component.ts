import { Component, inject } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';

/** Confirmación de la carga, que no se puede deshacer en bloque. Se cierra con `true` al confirmar. */
@Component({
  selector: 'app-import-confirm-dialog',
  imports: [TranslatePipe],
  template: `
    <div class="modal-header">
      <h4 class="modal-title">{{ 'DATA_IMPORT.CONFIRM_TITLE' | translate }}</h4>
    </div>
    <div class="modal-body">
      <p data-testid="confirm-body">{{ 'DATA_IMPORT.CONFIRM_BODY' | translate: { p0: salesToCreate } }}</p>
    </div>
    <div class="modal-footer">
      <button type="button" class="btn btn-light" data-testid="confirm-cancel" (click)="activeModal.dismiss()">
        {{ 'COMMON.CANCELAR' | translate }}
      </button>
      <button type="button" class="btn btn-warning" data-testid="confirm-execute" (click)="activeModal.close(true)">
        {{ 'DATA_IMPORT.EXECUTE' | translate }}
      </button>
    </div>
  `,
})
export class ImportConfirmDialogComponent {
  readonly activeModal = inject(NgbActiveModal);
  /** Ventas que se cargarán; lo fija quien abre el diálogo. */
  salesToCreate = 0;
}
