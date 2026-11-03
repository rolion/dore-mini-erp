import { tr } from '../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { EMPTY, Observable, expand, finalize, reduce } from 'rxjs';
import { Profile } from '../personnel/models/profile';
import { PersonnelApiService } from '../personnel/services/personnel-api.service';
import { Interval, Shift, Week } from './models/agenda';
import { AgendaApiService } from './services/agenda-api.service';

@Component({
  selector: 'app-agenda',
  imports: [TranslatePipe, ReactiveFormsModule],
  templateUrl: './agenda.component.html',
  styleUrl: './agenda.component.scss',
})
export class AgendaComponent {
  private api = inject(AgendaApiService);
  private personnel = inject(PersonnelApiService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;
  readonly days = [tr('AGENDA.AGENDA.LUNES'), tr('AGENDA.AGENDA.MARTES'), tr('AGENDA.AGENDA.MIERCOLES'), tr('AGENDA.AGENDA.JUEVES'), tr('AGENDA.AGENDA.VIERNES'), tr('AGENDA.AGENDA.SABADO'), tr('AGENDA.AGENDA.DOMINGO')];
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
  dialogError = '';
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

  formatDate(value: string): string {
    const [year, month, day] = value.slice(0, 10).split('-');
    return `${day}/${month}/${year}`;
  }

  formatDateTime(value: string): string {
    return `${this.formatDate(value)} ${value.slice(11, 16)}`;
  }

  dayEmpty(week: Week, index: number): boolean {
    const date = this.date(index);
    return !week.availability.some(item => item.starts.startsWith(date))
      && !week.shifts.some(item => item.day === index && item.valid_from <= date && item.valid_until >= date)
      && !week.absences.some(item => item.starts.slice(0, 10) <= date && item.ends.slice(0, 19) > date + 'T00:00:00');
  }

  open(dialog: HTMLDialogElement, prepare?: () => void): void {
    this.dialogError = '';
    prepare?.();
    dialog.showModal();
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
    this.api.week(this.selection.value, this.start).pipe(
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

  saveShift(dialog: HTMLDialogElement): void {
    if (this.shift.invalid || this.saving || this.loading || !this.week) return;
    this.save(this.api.saveShift(this.selection.value, this.shift.getRawValue(), this.editId),
      dialog, () => this.edit());
  }

  saveAbsence(dialog: HTMLDialogElement): void {
    if (this.absence.invalid || this.saving || this.loading || !this.week) return;
    this.save(this.api.saveAbsence(this.selection.value, this.absence.getRawValue()), dialog, () => this.absence.reset());
  }

  private save(request: Observable<unknown>, dialog: HTMLDialogElement, reset: () => void): void {
    this.dialogError = '';
    this.saved = '';
    this.saving = true;
    request.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving = false)).subscribe({
      next: () => { dialog.close(); reset(); this.saved = tr('AGENDA.AGENDA.CAMBIOS_GUARDADOS'); this.load(); },
      error: error => {
        this.dialogError = this.message(error);
        requestAnimationFrame(() => dialog.querySelector<HTMLElement>('[data-save-error]')?.focus());
      },
    });
  }

  private showError(error: unknown): void {
    this.error = this.message(error);
  }

  private message(error: unknown): string {
    const payload = error instanceof HttpErrorResponse ? error.error : null;
    const text = payload && typeof payload === 'object'
      ? Object.values(payload).flat().filter(value => typeof value === 'string').join(' ')
      : '';
    return text || tr('SETTINGS.SETTING.NO_SE_PUDO_COMPLETAR_LA');
  }
}
