import { tr } from '../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { EMPTY, Observable, expand, finalize, reduce } from 'rxjs';
import { Profile } from '../personnel/models/profile';
import { PersonnelApiService } from '../personnel/services/personnel-api.service';
import { Absence, Interval, RepeatMode, Shift, Week } from './models/agenda';
import { asFullDays, fullDayRange, minutesBetween, repeatUntil, shiftDate } from './models/agenda-dates';
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
  get days() {
    return [tr('AGENDA.AGENDA.LUNES'), tr('AGENDA.AGENDA.MARTES'), tr('AGENDA.AGENDA.MIERCOLES'), tr('AGENDA.AGENDA.JUEVES'), tr('AGENDA.AGENDA.VIERNES'), tr('AGENDA.AGENDA.SABADO'), tr('AGENDA.AGENDA.DOMINGO')];
  }
  get shortDays() {
    return [tr('AGENDA.AGENDA.LUN'), tr('AGENDA.AGENDA.MAR'), tr('AGENDA.AGENDA.MIE'), tr('AGENDA.AGENDA.JUE'), tr('AGENDA.AGENDA.VIE'), tr('AGENDA.AGENDA.SAB'), tr('AGENDA.AGENDA.DOM')];
  }
  readonly selection = this.fb.control('');
  readonly shift = this.fb.group({
    days: this.fb.control<number[]>([], Validators.required),
    starts: ['', Validators.required], ends: ['', Validators.required],
    repeat: this.fb.control<RepeatMode>('week'),
    valid_from: ['', Validators.required], valid_until: ['', Validators.required],
    breaks: this.fb.array<ReturnType<AgendaComponent['pause']>>([]),
  });
  readonly absence = this.fb.group({
    allDay: false,
    starts: ['', Validators.required], ends: ['', Validators.required],
    reason: ['', [Validators.required, Validators.maxLength(250)]],
  });
  people: Profile[] = [];
  week?: Week;
  start = this.currentMonday();
  editId?: number;
  copyOrigin?: number;
  absenceId?: number;
  confirmDelete = false;
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
    this.editAbsence();
    this.saved = '';
    this.load();
  }

  /** Prepara el diálogo de turno: alta (sin `item`), edición de un día o copia a otros días (`copy`). */
  edit(item?: Shift, copy = false): void {
    this.editId = copy ? undefined : item?.id;
    this.copyOrigin = copy ? item?.day : undefined;
    this.shift.controls.breaks.clear();
    this.shift.reset({
      days: item && !copy ? [item.day] : [],
      starts: item?.starts.slice(0, 5) ?? '', ends: item?.ends.slice(0, 5) ?? '',
      repeat: item ? 'custom' : 'week',
      valid_from: item?.valid_from ?? this.start, valid_until: item?.valid_until ?? repeatUntil('week', this.start),
    });
    for (const pause of item?.breaks ?? []) this.shift.controls.breaks.push(this.pause(pause));
  }

  toggleDay(day: number): void {
    const days = this.shift.controls.days;
    if (this.editId) days.setValue([day]);
    else days.setValue(days.value.includes(day) ? days.value.filter(item => item !== day) : [...days.value, day].sort());
    days.markAsDirty();
  }

  pickDays(days: number[]): void {
    this.shift.controls.days.setValue(days);
  }

  dayDisabled(day: number): boolean { return this.copyOrigin === day; }

  applyRepeat(): void {
    const { repeat } = this.shift.controls;
    if (repeat.value === 'custom') return;
    this.shift.patchValue({ valid_from: this.start, valid_until: repeatUntil(repeat.value, this.start) });
  }

  get shiftSummary(): string {
    const { days, starts, ends, valid_from, valid_until } = this.shift.getRawValue();
    if (!days.length || !starts || !ends || !valid_from || !valid_until) return '';
    return tr('AGENDA.AGENDA.RESUMEN_TURNO', {
      p0: days.map(day => this.shortDays[day]).join(', '), p1: starts.slice(0, 5), p2: ends.slice(0, 5),
      p3: this.formatDate(valid_from), p4: this.formatDate(valid_until),
    });
  }

  saveShift(dialog: HTMLDialogElement): void {
    if (this.shift.invalid || this.saving || this.loading || !this.week) return;
    const { days, starts, ends, valid_from, valid_until, breaks } = this.shift.getRawValue();
    const rest = { starts, ends, valid_from, valid_until, breaks };
    const request: Observable<unknown> = this.editId
      ? this.api.saveShift(this.selection.value, { ...rest, day: days[0] }, this.editId)
      : this.api.createShifts(this.selection.value, { ...rest, days });
    this.save(request, dialog, () => this.edit());
  }

  /** Prepara el diálogo de ausencia: alta (sin `item`) o edición. */
  editAbsence(item?: Absence, askDelete = false): void {
    this.absenceId = item?.id;
    this.confirmDelete = askDelete;
    const full = item ? asFullDays(item.starts, item.ends) : null;
    this.absence.reset({
      allDay: !!full,
      starts: full?.from ?? item?.starts.slice(0, 16) ?? '', ends: full?.to ?? item?.ends.slice(0, 16) ?? '',
      reason: item?.reason ?? '',
    });
  }

  toggleAllDay(): void {
    const { allDay, starts, ends } = this.absence.getRawValue();
    if (allDay) this.absence.patchValue({ starts: starts.slice(0, 10), ends: ends.slice(0, 10) });
    else this.absence.patchValue({
      starts: starts ? `${starts.slice(0, 10)}T00:00` : '', ends: ends ? `${ends.slice(0, 10)}T23:59` : '',
    });
  }

  get absenceDuration(): string {
    const { allDay, starts, ends } = this.absence.getRawValue();
    if (!starts || !ends) return '';
    if (allDay) {
      const days = minutesBetween(`${starts}T00:00`, `${shiftDate(ends, 1)}T00:00`) / 1440;
      if (days < 1) return '';
      return days === 1 ? tr('AGENDA.AGENDA.DURACION_UN_DIA') : tr('AGENDA.AGENDA.DURACION_DIAS', { p0: days });
    }
    const minutes = minutesBetween(starts, ends);
    return minutes > 0 ? tr('AGENDA.AGENDA.DURACION_HORAS', { p0: Math.floor(minutes / 60), p1: minutes % 60 }) : '';
  }

  saveAbsence(dialog: HTMLDialogElement): void {
    if (this.absence.invalid || this.saving || this.loading || !this.week) return;
    const { allDay, starts, ends, reason } = this.absence.getRawValue();
    const range = allDay ? fullDayRange(starts, ends) : { starts, ends };
    this.save(this.api.saveAbsence(this.selection.value, { ...range, reason }, this.absenceId), dialog, () => this.editAbsence());
  }

  removeAbsence(dialog: HTMLDialogElement): void {
    if (!this.absenceId || this.saving || this.loading || !this.week) return;
    this.save(this.api.deleteAbsence(this.selection.value, this.absenceId), dialog, () => this.editAbsence());
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
