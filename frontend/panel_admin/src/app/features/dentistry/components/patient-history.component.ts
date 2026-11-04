import { TranslatePipe } from '@ngx-translate/core';
import { tr } from '../../../core/i18n/translate';
import { HttpErrorResponse } from '@angular/common/http';
import { DatePipe } from '@angular/common';
import { Component, DestroyRef, Input, OnChanges, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize } from 'rxjs';
import { CLINICAL_FIELDS, PatientHistory } from '../models/patient';
import { DentistryApiService, errorMessage } from '../services/dentistry-api.service';

@Component({
  selector: 'app-patient-history', imports: [TranslatePipe, DatePipe], template: `
    <h5 class="h6 fw-semibold mb-3">{{ (clinical ? 'DENTISTRY.PATIENT_HISTORY.CLINICAL_CHANGES' : 'DENTISTRY.PATIENT_HISTORY.ADMIN_CHANGES') | translate }}</h5>
    @if (loading) { <p role="status">{{ 'CUSTOMERS.CUSTOMER_PURCHASE_HISTORY.CARGANDO_HISTORIAL' | translate }}</p> }
    @if (error) {
      <div class="alert alert-danger" role="alert">{{ error }}
        <button class="btn btn-sm btn-light" type="button" (click)="load()">{{ 'COMMON.REINTENTAR' | translate }}</button>
      </div>
    }
    @if (!loading && !error && !rows.length) { <p class="text-muted">{{ 'SETTINGS.SETTINGS_HISTORY.SIN_CAMBIOS_REGISTRADOS' | translate }}</p> }
    <ol class="list-group list-group-flush border-start">
      @for (row of rows; track row.id) {
        <li class="list-group-item bg-transparent py-3">
          <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
            <span class="badge bg-secondary-subtle text-secondary-emphasis">{{ action(row.action) }}</span>
            <time class="small text-muted" [attr.datetime]="row.created_at">{{ row.created_at | date:'dd/MM/yyyy HH:mm' }}</time>
            <strong class="small text-break">{{ row.author_name }}</strong>
          </div>
          <ul class="list-unstyled mb-0">
            @for (change of changes(row); track change.key) {
              <li class="mb-2">
                <div class="fw-semibold small">{{ change.label }}</div>
                <div class="row g-2 small text-break">
                  <div class="col-sm-6"><span class="text-muted d-block">{{ 'DENTISTRY.PATIENT_HISTORY.BEFORE' | translate }}</span>{{ change.before }}</div>
                  <div class="col-sm-6"><span class="text-muted d-block">{{ 'DENTISTRY.PATIENT_HISTORY.AFTER' | translate }}</span>{{ change.after }}</div>
                </div>
              </li>
            }
          </ul>
        </li>
      }
    </ol>
    @if (next || previous) {
      <div class="d-flex flex-wrap gap-2 align-items-center mt-3">
        <button type="button" class="btn btn-light" [disabled]="loading || !previous" (click)="move(-1)">{{ 'DENTISTRY.PATIENT_HISTORY.PREVIOUS' | translate }}</button>
        <span>{{ 'DENTISTRY.PATIENT_HISTORY.PAGE' | translate: { p0: page } }}</span>
        <button type="button" class="btn btn-light" [disabled]="loading || !next" (click)="move(1)">{{ 'DENTISTRY.PATIENT_HISTORY.NEXT' | translate }}</button>
      </div>
    }

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

  next = false;
  previous = false;
  ngOnChanges() { this.page = 1; this.load(); }
  move(delta: number) { if (!this.loading) { this.page += delta; this.load(); } }
  load() {
    this.error = ''; this.loading = true;
    this.api.history(this.patientId, this.clinical, this.page).pipe(
      finalize(() => this.loading = false), takeUntilDestroyed(this.destroyRef),
    ).subscribe({ next: result => {
      this.rows = result.results; this.next = !!result.next; this.previous = !!result.previous;
    }, error: (error: HttpErrorResponse) => { this.rows = []; this.error = errorMessage(error); } });
  }
  action(value?: string) {
    return value === 'create' ? tr('DENTISTRY.PATIENT_HISTORY.ALTA') : value === 'archive' ? tr('DENTISTRY.PATIENT_HISTORY.ARCHIVO') : value === 'activate' ? tr('DENTISTRY.PATIENT_HISTORY.REACTIVACION') : tr('DENTISTRY.PATIENT_HISTORY.EDICION');
  }
  changes(row: PatientHistory) {
    const labels: Record<string, string> = {
      active: tr('DENTISTRY.PATIENT_HISTORY.ESTADO_DEL_PERFIL'), birth_date: tr('DENTISTRY.PATIENT_HISTORY.FECHA_DE_NACIMIENTO'), responsible_name: tr('DENTISTRY.PATIENT_HISTORY.NOMBRE_DEL_RESPONSABLE'),
      responsible_phone: tr('DENTISTRY.PATIENT_HISTORY.TELEFONO_DEL_RESPONSABLE'), ...Object.fromEntries(CLINICAL_FIELDS.map(field => [field.key, field.label])),
    };
    return Object.keys(row.after).filter(key => (row.before[key] ?? '') !== (row.after[key] ?? '')).map(key => ({
      key, label: labels[key] ?? key, before: this.display(row.before[key], key), after: this.display(row.after[key], key),
    }));
  }
  private display(value: string | boolean | null | undefined, key: string) {
    if (typeof value === 'boolean') return value ? tr('DENTISTRY.PATIENT_HISTORY.ACTIVO') : tr('DENTISTRY.PATIENT_HISTORY.ARCHIVADO');
    if (key === 'birth_date' && typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
      return value.split('-').reverse().join('/');
    }
    return value || tr('DENTISTRY.PATIENT_HISTORY.NO_INFORMADO');
  }
}
