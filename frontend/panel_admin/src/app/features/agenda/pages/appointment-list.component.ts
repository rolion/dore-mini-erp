import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize, forkJoin } from 'rxjs';
import { tr } from '../../../core/i18n/translate';
import { Profile } from '../../personnel/models/profile';
import { PersonnelApiService } from '../../personnel/services/personnel-api.service';
import {
  APPOINTMENT_STATUSES, Appointment, AppointmentFilters, AppointmentStatus, STATUS_CLASSES, Slot, statusLabel,
} from '../models/appointment';
import { AppointmentsApiService, formatDateTime } from '../services/appointments-api.service';
import { fetchAll } from '../services/fetch-all';

interface DayGroup {
  date: string;
  appointments: Appointment[];
  slots: Slot[];
}

/** Agenda → Citas: listado con filtros y calendario diario/semanal textual (ver DDR de citas). */
@Component({
  selector: 'app-appointment-list',
  imports: [ReactiveFormsModule, RouterLink, TranslatePipe],
  templateUrl: './appointment-list.component.html',
  styleUrl: './appointment-list.component.scss',
})
export class AppointmentListComponent implements OnInit {
  private api = inject(AppointmentsApiService);
  private personnel = inject(PersonnelApiService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  readonly statuses = APPOINTMENT_STATUSES;
  readonly statusLabel = statusLabel;
  readonly classes = STATUS_CLASSES;
  readonly formatDateTime = formatDateTime;
  readonly filters = this.fb.group({ from: '', to: '', professional: '', status: '', search: '' });
  readonly calendar = this.fb.group({ professional: '', date: this.today(), span: '1' });

  mode: 'list' | 'calendar' = 'list';
  people: Profile[] = [];
  rows: Appointment[] = [];
  groups: DayGroup[] = [];
  count = 0;
  page = 1;
  loading = false;
  error = '';
  /** Identifica la última consulta: la respuesta o el cierre de una anterior no pisa el estado de la vigente. */
  private requestId = 0;

  ngOnInit(): void {
    const query = this.route.snapshot.queryParamMap;
    this.filters.patchValue({
      from: query.get('from') ?? '', to: query.get('to') ?? '', professional: query.get('professional') ?? '',
      status: query.get('status') ?? '', search: query.get('search') ?? '',
    });
    fetchAll(page => this.personnel.list('professionals', { page, page_size: 100 })).pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: people => this.people = people, error: () => this.error = tr('AGENDA.CITAS.ERR_CARGAR_PROFESIONALES') });
    if (query.get('view') === 'calendar') {
      this.calendar.patchValue({
        professional: query.get('cal_professional') ?? '', date: query.get('cal_date') || this.today(),
        span: query.get('cal_span') === '7' ? '7' : '1',
      });
      this.mode = 'calendar';
      this.loadCalendar();
      return;
    }
    this.search(Math.max(1, Number(query.get('page')) || 1));
  }

  get hasFilters(): boolean {
    return Object.values(this.filters.getRawValue()).some(value => value !== '');
  }

  today(): string {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/La_Paz', year: 'numeric', month: '2-digit', day: '2-digit',
    }).format(new Date());
    return parts;
  }

  setMode(mode: 'list' | 'calendar'): void {
    this.mode = mode;
    this.error = '';
    if (mode === 'list') this.search(); else this.loadCalendar();
  }

  search(page = 1): void {
    this.page = page;
    const raw = this.filters.getRawValue();
    const filters: AppointmentFilters = { ...raw, status: raw.status as AppointmentStatus | '', page };
    this.syncUrl(page);
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
          // Una página que dejó de existir (enlace viejo, menos resultados) vuelve a la primera en vez de quedar atascada.
          if (failure.status === 404 && page > 1) this.search(1);
          else this.error = tr('AGENDA.CITAS.ERR_CARGAR_CITAS');
        },
      });
  }

  /** Filtros, página, vista y calendario viven en la URL: se recuperan al recargar, compartir o volver desde el detalle. */
  private syncUrl(page: number): void {
    const inList = this.mode === 'list';
    const queryParams: Record<string, string | number | null> = { page: inList && page > 1 ? page : null };
    const calendar = this.calendar.getRawValue();
    for (const [key, value] of Object.entries(this.filters.getRawValue())) queryParams[key] = inList ? value || null : null;
    queryParams['view'] = inList ? null : 'calendar';
    queryParams['cal_professional'] = inList ? null : calendar.professional || null;
    queryParams['cal_date'] = inList ? null : calendar.date;
    queryParams['cal_span'] = inList ? null : calendar.span;
    void this.router.navigate([], { relativeTo: this.route, queryParams, replaceUrl: true });
  }

  clear(): void {
    this.filters.reset();
    this.search();
  }

  get pages(): number {
    return Math.max(1, Math.ceil(this.count / 20));
  }

  private addDays(date: string, days: number): string {
    const value = new Date(`${date}T00:00:00Z`);
    value.setUTCDate(value.getUTCDate() + days);
    return value.toISOString().slice(0, 10);
  }

  loadCalendar(): void {
    const { professional, date, span } = this.calendar.getRawValue();
    this.syncUrl(1);
    this.groups = [];
    this.error = '';
    if (!professional || !date) return;
    const last = this.addDays(date, Number(span) - 1);
    this.loading = true;
    forkJoin({
      appointments: fetchAll(page => this.api.list({ professional, from: date, to: last, page_size: 100, page })),
      free: this.api.freeSlots(professional, date, last),
    }).pipe(
      takeUntilDestroyed(this.destroyRef), finalize(() => this.loading = false),
    ).subscribe({
      next: ({ appointments: items, free }) => {
        const groups: DayGroup[] = [];
        for (let i = 0; i < Number(span); i++) {
          const day = this.addDays(date, i);
          groups.push({
            date: day,
            appointments: items.filter(item => item.starts.startsWith(day) && item.status !== 'cancelled'),
            slots: free.slots.filter(slot => slot.starts.startsWith(day)),
          });
        }
        this.groups = groups;
      },
      error: () => this.error = tr('AGENDA.CITAS.ERR_CARGAR_CALENDARIO'),
    });
  }

  newQuery(slot: Slot): Record<string, string> {
    return { professional: this.calendar.controls.professional.value, starts: slot.starts.slice(0, 16) };
  }

  formatDay(value: string): string {
    const [year, month, day] = value.split('-');
    return `${day}/${month}/${year}`;
  }

  time(value: string): string {
    return value.slice(11, 16);
  }
}
