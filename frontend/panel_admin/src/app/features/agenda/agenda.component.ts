import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { EMPTY, expand, finalize, reduce } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Profile } from '../personnel/models/profile';
import { PersonnelApiService } from '../personnel/services/personnel-api.service';

interface Interval { starts: string; ends: string }
interface Shift extends Interval {
  id: number;
  day: number;
  valid_from: string;
  valid_until: string;
  breaks: Interval[];
}
interface Week {
  timezone: string;
  shifts: Shift[];
  availability: Interval[];
  absences: (Interval & { id: number; reason: string })[];
}

@Component({
  selector: 'app-agenda',
  imports: [ReactiveFormsModule],
  templateUrl: './agenda.component.html',
})
export class AgendaComponent {
  private http = inject(HttpClient);
  private personnel = inject(PersonnelApiService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;
  readonly days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
  readonly selection = this.fb.control('');
  readonly shift = this.fb.group({
    day: 0, starts: ['', Validators.required], ends: ['', Validators.required],
    valid_from: ['', Validators.required], valid_until: ['', Validators.required],
    breaks: this.fb.array<ReturnType<AgendaComponent['pause']>>([]),
  });
  readonly absence = this.fb.group({
    starts: ['', Validators.required], ends: ['', Validators.required],
    reason: ['', [Validators.required, Validators.maxLength(250)]],
  });
  people: Profile[] = [];
  week?: Week;
  start = this.currentMonday();
  editId?: number;
  loading = false;
  loadingPeople = false;
  saving = false;
  error = '';
  saved = '';

  constructor() { this.loadPeople(); }

  loadPeople(): void {
    this.error = '';
    this.loadingPeople = true;
    let page = 1;
    const list = () => this.personnel.list('professionals', { page, page_size: 100 });
    list().pipe(
      expand(result => { page++; return result.next ? list() : EMPTY; }),
      reduce((all, result) => [...all, ...result.results], [] as Profile[]),
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.loadingPeople = false),
    ).subscribe({ next: people => this.people = people, error: error => this.showError(error) });
  }

  private currentMonday(): string {
    const local = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/La_Paz', year: 'numeric', month: '2-digit', day: '2-digit' })
      .formatToParts(new Date());
    const value = (key: string) => Number(local.find(part => part.type === key)?.value);
    const date = new Date(Date.UTC(value('year'), value('month') - 1, value('day')));
    return this.dateAt(date, -((date.getUTCDay() + 6) % 7));
  }

  private dateAt(date: Date, offset: number): string {
    const copy = new Date(date);
    copy.setUTCDate(copy.getUTCDate() + offset);
    return copy.toISOString().slice(0, 10);
  }

  date(day: number): string { return this.dateAt(new Date(this.start), day); }

  private get base(): string {
    return `${environment.apiUrl}/agenda/${this.selection.value}/`;
  }

  move(offset: number): void {
    this.start = this.date(offset);
    this.load();
  }

  load(): void {
    this.week = undefined;
    this.error = '';
    if (!this.selection.value) return;
    this.loading = true;
    this.http.get<Week>(this.base + 'week/', { params: { start: this.start } }).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.loading = false),
    ).subscribe({ next: week => this.week = week, error: error => this.showError(error) });
  }

  pause(interval: Interval = { starts: '', ends: '' }) {
    return this.fb.group({ starts: [interval.starts, Validators.required], ends: [interval.ends, Validators.required] });
  }

  selectProfessional(): void {
    this.edit();
    this.absence.reset();
    this.saved = '';
    this.load();
  }

  edit(item?: Shift): void {
    this.editId = item?.id;
    this.shift.controls.breaks.clear();
    this.shift.reset(item ?? { day: 0, valid_from: this.start, valid_until: this.date(6) });
    for (const pause of item?.breaks ?? []) this.shift.controls.breaks.push(this.pause(pause));
  }

  saveShift(): void {
    if (this.shift.invalid || this.saving || this.loading || !this.week) return;
    const url = this.base + 'shifts/';
    const body = this.shift.getRawValue();
    this.save(this.editId ? this.http.put(url + this.editId + '/', body) : this.http.post(url, body),
      () => this.edit());
  }

  saveAbsence(): void {
    if (this.absence.invalid || this.saving || this.loading || !this.week) return;
    this.save(this.http.post(this.base + 'absences/', this.absence.getRawValue()), () => this.absence.reset());
  }

  private save(request: ReturnType<HttpClient['post']>, reset: () => void): void {
    this.error = '';
    this.saved = '';
    this.saving = true;
    request.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving = false)).subscribe({
      next: () => { reset(); this.saved = 'Cambios guardados.'; this.load(); },
      error: error => this.showError(error),
    });
  }

  private showError(error: unknown): void {
    const payload = error instanceof HttpErrorResponse ? error.error : null;
    this.error = payload && typeof payload === 'object'
      ? Object.values(payload).flat().filter(value => typeof value === 'string').join(' ')
      : '';
    this.error ||= 'No se pudo completar la operación. Inténtalo de nuevo.';
  }
}
