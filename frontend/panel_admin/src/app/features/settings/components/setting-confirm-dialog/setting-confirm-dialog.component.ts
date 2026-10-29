import { Component, inject } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';

/** Confirma un ajuste antes de guardarlo activado. Quien lo abre fija `title`, `message` y `confirmLabel`. */
@Component({
  selector: 'app-setting-confirm-dialog',
  templateUrl: './setting-confirm-dialog.component.html',
})
export class SettingConfirmDialogComponent {
  title = '';
  message = '';
  confirmLabel = 'Confirmar';

  readonly activeModal = inject(NgbActiveModal);
}
