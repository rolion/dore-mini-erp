import { HttpErrorResponse } from '@angular/common/http';
import { DatePipe } from '@angular/common';
import { Component, DestroyRef, Input, OnChanges, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize } from 'rxjs';
import { CLINICAL_FIELDS, PatientHistory } from '../models/patient';
import { DentistryApiService, errorMessage } from '../services/dentistry-api.service';

@Component({
  selector: 'app-patient-history', imports: [DatePipe], template: `
    <h5 class="mt-4">Historial de cambios {{ clinical ? 'clínicos' : 'administrativos' }}</h5>
    @if (loading) { <p aria-live="polite">Cargando historial…</p> }
    @if (error) { <div class="alert alert-danger" role="alert">{{ error }} <button class="btn btn-light" type="button" (click)="load()">Reintentar</button></div> }
    @if (!loading && !error && !rows.length) { <p>Sin cambios registrados.</p> }
    @for (row of rows; track row.id) {
      <div class="border rounded p-3 mb-2">
        <p><strong>{{ row.author_name }}</strong> · {{ row.created_at | date:'dd/MM/yyyy HH:mm' }} · {{ action(row.action) }}</p>
        <div class="table-responsive"><table class="table"><thead><tr><th>Dato</th><th>Antes</th><th>Después</th></tr></thead><tbody>
          @for (change of changes(row); track change.key) {
            <tr><th scope="row">{{ change.label }}</th><td class="text-break">{{ change.before }}</td><td class="text-break">{{ change.after }}</td></tr>
          }
        </tbody></table></div>
      </div>
    }
    @if (count > rows.length) { <div class="d-flex gap-2 align-items-center">
      <button type="button" class="btn btn-light" [disabled]="loading || !previous" (click)="move(-1)">Anterior</button>
      <span>Página {{ page }}</span>
      <button type="button" class="btn btn-light" [disabled]="loading || !next" (click)="move(1)">Siguiente</button>
    </div> }
  `,
})
export class PatientHistoryComponent implements OnChanges {
  @Input({ required: true }) patientId = '';
  @Input() clinical = true;
  @Input() revision = 0;
  private api = inject(DentistryApiService);
  private destroyRef = inject(DestroyRef);
  rows: PatientHistory[] = [];
  loading = false;
  error = '';
  page = 1;
  count = 0;
  next = false;
  previous = false;
  ngOnChanges() { this.page = 1; this.load(); }
  move(delta: number) { if (!this.loading) { this.page += delta; this.load(); } }
  load() {
    this.error = ''; this.loading = true;
    this.api.history(this.patientId, this.clinical, this.page).pipe(
      finalize(() => this.loading = false), takeUntilDestroyed(this.destroyRef),
    ).subscribe({ next: result => {
      this.rows = result.results; this.count = result.count; this.next = !!result.next; this.previous = !!result.previous;
    }, error: (error: HttpErrorResponse) => { this.rows = []; this.error = errorMessage(error); } });
  }
  action(value?: string) {
    return value === 'create' ? 'Alta' : value === 'archive' ? 'Archivo' : value === 'activate' ? 'Reactivación' : 'Edición';
  }
  changes(row: PatientHistory) {
    const labels: Record<string, string> = {
      active: 'Estado del perfil', birth_date: 'Fecha de nacimiento', responsible_name: 'Nombre del responsable',
      responsible_phone: 'Teléfono del responsable', ...Object.fromEntries(CLINICAL_FIELDS.map(field => [field.key, field.label])),
    };
    return Object.keys(row.after).filter(key => row.before[key] !== row.after[key]).map(key => ({
      key, label: labels[key] ?? key, before: this.display(row.before[key], key), after: this.display(row.after[key], key),
    }));
  }
  private display(value: string | boolean | null | undefined, key: string) {
    if (typeof value === 'boolean') return value ? 'Activo' : 'Archivado';
    if (key === 'birth_date' && typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
      return value.split('-').reverse().join('/');
    }
    return value || 'No informado';
  }
}
