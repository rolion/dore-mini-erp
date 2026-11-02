import { Component, DestroyRef, EventEmitter, Input, Output, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize } from 'rxjs';
import Swal from 'sweetalert2';
import { CatalogService, ServiceApiError } from '../models/service';
import { ServicesApiService } from '../services/services-api.service';

@Component({
  selector: 'app-service-toggle',
  template: `
    <button type="button" [class]="compact ? 'btn btn-tbl-edit btn-tbl-toggle h-auto' : 'btn btn-warning'"
      [disabled]="busy" (click)="toggle()" [title]="label" [attr.aria-label]="label">
      @if (compact) { <i class="material-icons" aria-hidden="true">power_settings_new</i> }
      @else { {{ busy ? 'Guardando…' : label }} }
    </button>
    @if (error) { <small role="alert" class="text-danger d-block">{{ error }}</small> }
    @if (success) { <small role="status" class="text-success d-block">{{ success }}</small> }
  `,
})
export class ServiceToggleComponent {
  @Input({ required: true }) service!: CatalogService;
  @Input() compact = false;
  @Output() updated = new EventEmitter<CatalogService>();
  private api = inject(ServicesApiService);
  private destroyRef = inject(DestroyRef);
  busy = false;
  error = '';
  success = '';
  get label(): string { return this.service.active ? 'Desactivar' : 'Activar'; }

  async toggle(): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    this.error = '';
    this.success = '';
    const result = await Swal.fire({ title: `¿${this.label} ${this.service.name}?`,
      text: this.service.active ? 'No se ofrecerá en nuevos usos. Su historial se conserva.' : 'Volverá a estar disponible para nuevos usos.',
      showCancelButton: true, confirmButtonText: this.label, cancelButtonText: 'Cancelar' });
    if (!result.isConfirmed || this.destroyRef.destroyed) { this.busy = false; return; }
    this.api.setActive(this.service.id, !this.service.active).pipe(
      finalize(() => this.busy = false), takeUntilDestroyed(this.destroyRef),
    ).subscribe({ next: service => {
      this.success = service.active ? 'Servicio activado.' : 'Servicio desactivado.';
      this.updated.emit(service);
    }, error: (error: ServiceApiError) => this.error = error.message });
  }
}
