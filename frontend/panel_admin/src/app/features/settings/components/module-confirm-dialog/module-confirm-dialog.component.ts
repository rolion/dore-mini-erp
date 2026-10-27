import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { AppModule, ModulesApiError } from '../../../../core/models/module';
import { AuthService } from '../../../../core/service/auth.service';
import { ModulesService } from '../../../../core/service/modules.service';

export type ModuleAction = 'enable' | 'disable';

/**
 * Confirma y ejecuta Habilitar/Deshabilitar de un módulo mostrando antes un resumen. Se abre con `NgbModal`,
 * quien lo abre fija `module`, `action` y `affected`; se cierra con el módulo actualizado.
 */
@Component({
  selector: 'app-module-confirm-dialog',
  templateUrl: './module-confirm-dialog.component.html',
})
export class ModuleConfirmDialogComponent {
  module!: AppModule;
  action: ModuleAction = 'enable';
  /** Nombres de los módulos habilitados que dependen de este (relevantes al deshabilitar). */
  affected: string[] = [];
  saving = false;
  serverError = '';

  readonly activeModal = inject(NgbActiveModal);
  private modules = inject(ModulesService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);
  private auth = inject(AuthService);

  get isEnable(): boolean {
    return this.action === 'enable';
  }

  get companyName(): string {
    return this.auth.currentUserValue?.company?.name ?? '—';
  }

  get requiredNames(): string[] {
    return this.module.requires.map((link) => link.name);
  }

  confirm(): void {
    if (this.saving) {
      return;
    }
    this.saving = true;
    this.serverError = '';
    const request = this.isEnable ? this.modules.enable(this.module.key) : this.modules.disable(this.module.key);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.saving = false;
        this.toastr.success(this.isEnable ? 'Módulo habilitado' : 'Módulo deshabilitado');
        this.activeModal.close(updated);
      },
      error: (err: ModulesApiError) => {
        this.saving = false;
        this.serverError = err.message;
      },
    });
  }
}
