import { Component } from '@angular/core';
import { inject } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { Account } from '../../models/accounting';

/**
 * Confirma la desactivación de una cuenta. Si la usan métodos activos (`methods`, etiquetas) el diálogo solo informa:
 * hay que reasignarlos o desactivarlos primero (el servidor lo vuelve a comprobar).
 */
@Component({
  selector: 'app-deactivate-dialog',
  templateUrl: './deactivate-dialog.component.html',
  styleUrl: './deactivate-dialog.component.scss',
  imports: [TranslatePipe],
})
export class DeactivateDialogComponent {
  account!: Account;
  /** Etiquetas de los métodos activos que usan la cuenta. */
  methods: string[] = [];

  readonly activeModal = inject(NgbActiveModal);

  get blocked(): boolean {
    return this.methods.length > 0;
  }

  get methodNames(): string {
    return this.methods.join(', ');
  }
}
