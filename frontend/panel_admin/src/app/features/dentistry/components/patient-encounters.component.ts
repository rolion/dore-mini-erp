import { Component, DestroyRef, Input, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TranslatePipe } from '@ngx-translate/core';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { ModulesService } from '../../../core/service/modules.service';
import { PatientEncounter, encounterStatusLabel, encounterTone } from '../models/encounter';
import { formatDateTime } from '../../agenda/services/appointments-api.service';
import { EncountersApiService, encounterFailure } from '../services/encounters-api.service';

/** Tarjeta «Atenciones» de la ficha del paciente: historial de solo lectura, cada fila enlaza a su atención. */
@Component({
  selector: 'app-patient-encounters',
  imports: [RouterLink, TranslatePipe],
  template: `
    @if (!unavailable) {
    <div class="card shadow-sm border-0 mb-4">
      <div class="card-body">
        <h5 class="card-title">{{ 'DENTISTRY.ENCOUNTER.HISTORIAL_ATENCIONES' | translate }}</h5>
        @if (loading) { <p role="status" class="mb-0">{{ 'DENTISTRY.ENCOUNTER.CARGANDO' | translate }}</p> }
        @if (error) { <p class="alert alert-danger mb-0" role="alert">{{ error }}</p> }
        @if (!loading && !error && !items.length) { <p class="text-muted mb-0">{{ 'DENTISTRY.ENCOUNTER.SIN_ATENCIONES' | translate }}</p> }
        @if (items.length) {
          <ul class="list-unstyled mb-0">
            @for (item of items; track item.id) {
              <li class="d-flex flex-wrap gap-2 align-items-center py-1">
                <a [routerLink]="['/pocketbiz/dentistry/appointments', item.appointment_id]">{{ item.appointment_code ? item.appointment_code + ' · ' : '' }}{{ formatDateTime(item.started_at) }}</a>
                <span>{{ item.service_name }} · {{ item.professional_name }}</span>
                <span class="badge" [class]="tone(item.status)">{{ label(item.status) }}</span>
                @if (item.has_odontogram) { <small class="text-muted">{{ 'DENTISTRY.ENCOUNTER.CON_ODONTOGRAMA' | translate }}</small> }
              </li>
            }
          </ul>
        }
      </div>
    </div>
    }`,
})
export class PatientEncountersComponent implements OnInit {
  private api = inject(EncountersApiService);
  private destroyRef = inject(DestroyRef);
  private modules = inject(ModulesService);

  @Input({ required: true }) patientId = '';

  readonly tone = encounterTone;
  readonly formatDateTime = formatDateTime;
  items: PatientEncounter[] = [];
  loading = true;
  error = '';

  label(status: PatientEncounter['status']): string {
    return encounterStatusLabel(status);
  }

  /** Sin Agenda habilitada no hay atenciones que mostrar: la tarjeta se oculta en vez de fallar. */
  get unavailable(): boolean {
    return this.modules.isDisabled('agenda');
  }

  ngOnInit(): void {
    if (this.unavailable) {
      this.loading = false;
      return;
    }
    this.api.forPatient(this.patientId).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.loading = false))
      .subscribe({ next: page => this.items = page.results, error: failure => this.error = encounterFailure(failure).message });
  }
}
