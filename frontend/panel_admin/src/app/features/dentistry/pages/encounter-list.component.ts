import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { tr } from '../../../core/i18n/translate';
import { APPOINTMENT_STATUSES, STATUS_CLASSES, statusLabel } from '../../agenda/models/appointment';
import { formatDateTime } from '../../agenda/services/appointments-api.service';
import { fetchAll } from '../../agenda/services/fetch-all';
import { Profile } from '../../personnel/models/profile';
import { PersonnelApiService } from '../../personnel/services/personnel-api.service';
import {
  ENCOUNTER_CLASSES, ENCOUNTER_STATUSES, EncounterFilters, EncounterListItem, EncounterStatus, encounterStatusLabel,
  AppointmentStatusValue,
} from '../models/encounter';
import { EncountersApiService } from '../services/encounters-api.service';

const PAGE_SIZE = 20;

/** Odontología → Citas: listado clínico de las citas de pacientes odontológicos (ver DDR de atención). */
@Component({
  selector: 'app-encounter-list',
  imports: [ReactiveFormsModule, RouterLink, TranslatePipe],
  templateUrl: './encounter-list.component.html',
  styleUrl: './encounter-list.component.scss',
})
export class EncounterListComponent implements OnInit {
  private api = inject(EncountersApiService);
  private personnel = inject(PersonnelApiService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  readonly statuses = APPOINTMENT_STATUSES;
  readonly encounterStatuses = ENCOUNTER_STATUSES;
  readonly statusLabel = statusLabel;
  readonly encounterLabel = encounterStatusLabel;
  readonly appointmentClasses = STATUS_CLASSES;
  readonly encounterClasses = ENCOUNTER_CLASSES;
  readonly formatDateTime = formatDateTime;
  readonly filters = this.fb.group({ from: this.today(), to: this.today(), professional: '', search: '', status: '', encounter_status: '' });

  people: Profile[] = [];
  rows: EncounterListItem[] = [];
  count = 0;
  page = 1;
  loading = false;
  error = '';
  private requestId = 0;

  ngOnInit(): void {
    const query = this.route.snapshot.queryParamMap;
    const keys = ['from', 'to', 'professional', 'search', 'status', 'encounter_status'] as const;
    for (const key of keys) {
      const value = query.get(key);
      if (value !== null) this.filters.controls[key].setValue(value);
    }
    fetchAll(page => this.personnel.list('professionals', { page, page_size: 100 })).pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: people => this.people = people, error: () => this.error = tr('DENTISTRY.ENCOUNTER.ERR_PROFESIONALES') });
    this.search(Math.max(1, Number(query.get('page')) || 1));
  }

  today(): string {
    return new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/La_Paz', year: 'numeric', month: '2-digit', day: '2-digit',
    }).format(new Date());
  }

  get hasFilters(): boolean {
    const raw = this.filters.getRawValue();
    return !!(raw.professional || raw.search || raw.status || raw.encounter_status || raw.from !== this.today() || raw.to !== this.today());
  }

  get pages(): number {
    return Math.max(1, Math.ceil(this.count / PAGE_SIZE));
  }

  search(page = 1): void {
    this.page = page;
    const raw = this.filters.getRawValue();
    const filters: EncounterFilters = {
      ...raw, status: raw.status as AppointmentStatusValue | '', encounter_status: raw.encounter_status as EncounterStatus | '', page,
    };
    const queryParams: Record<string, string | number | null> = { page: page > 1 ? page : null };
    for (const [key, value] of Object.entries(raw)) queryParams[key] = value || null;
    void this.router.navigate([], { relativeTo: this.route, queryParams, replaceUrl: true });
    const requestId = ++this.requestId;
    this.loading = true;
    this.error = '';
    this.api.list(filters).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => { if (requestId === this.requestId) this.loading = false; }),
    ).subscribe({
      next: result => { if (requestId === this.requestId) { this.rows = result.results; this.count = result.count; } },
      error: (failure: HttpErrorResponse) => {
        if (requestId !== this.requestId) return;
        if (failure.status === 404 && page > 1) this.search(1);
        else this.error = failure.status === 400 ? tr('DENTISTRY.ENCOUNTER.ERR_RANGO') : tr('DENTISTRY.ENCOUNTER.ERR_CARGAR_CITAS');
      },
    });
  }

  clear(): void {
    this.filters.reset({ from: this.today(), to: this.today(), professional: '', search: '', status: '', encounter_status: '' });
    this.search();
  }

  time(value: string): string {
    return value.slice(11, 16);
  }

  shortId(id: string): string {
    return id.slice(0, 8);
  }
}
