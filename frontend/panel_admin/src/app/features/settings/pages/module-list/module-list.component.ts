import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { AppModule } from '../../../../core/models/module';
import { ModulesService } from '../../../../core/service/modules.service';
import { SettingsHistoryComponent } from '../../components/settings-history/settings-history.component';
import {
  ModuleAction,
  ModuleConfirmDialogComponent,
} from '../../components/module-confirm-dialog/module-confirm-dialog.component';

@Component({
  selector: 'app-module-list',
  templateUrl: './module-list.component.html',
  styleUrl: './module-list.component.scss',
  imports: [RouterLink, SettingsHistoryComponent],
})
export class ModuleListComponent implements OnInit {
  tab: 'general' | 'history' = 'general';
  modules: AppModule[] = [];
  loading = false;
  errorMessage = '';

  private service = inject(ModulesService);
  private modal = inject(NgbModal);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.service.modules$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((modules) => {
      if (modules) {
        this.modules = modules;
      }
    });
    this.load();
  }

  select(tab: 'general' | 'history'): void {
    this.tab = tab;
  }

  load(): void {
    this.loading = true;
    this.errorMessage = '';
    this.service
      .load()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => (this.loading = false),
        error: (err: Error) => {
          this.loading = false;
          this.errorMessage = err.message;
        },
      });
  }

  /** Nombres de los módulos habilitados que requieren a `module`. */
  dependentsOf(module: AppModule): string[] {
    return this.modules.filter((m) => m.enabled && m.requires.some((r) => r.key === module.key)).map((m) => m.name);
  }

  disableBlockedBy(module: AppModule): string[] {
    return module.enabled && !module.isBase ? this.dependentsOf(module) : [];
  }

  blockedReason(module: AppModule): string {
    if (module.enabled) {
      const dependents = this.disableBlockedBy(module);
      return dependents.length ? `Lo requieren: ${dependents.join(', ')}` : '';
    }
    return module.missingRequires.length ? `Requiere habilitar primero: ${module.missingRequires.join(', ')}` : '';
  }

  open(module: AppModule): void {
    if (this.blockedReason(module)) {
      return;
    }
    const action: ModuleAction = module.enabled ? 'disable' : 'enable';
    const ref = this.modal.open(ModuleConfirmDialogComponent);
    const dialog = ref.componentInstance as ModuleConfirmDialogComponent;
    dialog.module = module;
    dialog.action = action;
    dialog.affected = this.dependentsOf(module);
    // Tras confirmar se recarga: habilitar uno puede liberar o bloquear a otros módulos.
    ref.result.then(
      () => this.load(),
      () => undefined,
    );
  }
}
