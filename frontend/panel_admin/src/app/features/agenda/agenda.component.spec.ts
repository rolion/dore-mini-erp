import { provideTestTranslations } from '../../core/i18n/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { Profile } from '../personnel/models/profile';
import { PersonnelApiService } from '../personnel/services/personnel-api.service';
import { AgendaComponent } from './agenda.component';
import { Absence, Shift, Week } from './models/agenda';
import { AgendaApiService } from './services/agenda-api.service';

describe('AgendaComponent', () => {
  let fixture: ComponentFixture<AgendaComponent>;
  let component: AgendaComponent;
  let api: jasmine.SpyObj<AgendaApiService>;
  const dialog = { close: jasmine.createSpy('close'), querySelector: () => null } as unknown as HTMLDialogElement;
  const shift: Shift = {
    id: 5, day: 2, starts: '08:00:00', ends: '20:00:00', valid_from: '2026-11-02', valid_until: '2026-11-08',
    breaks: [{ starts: '12:00:00', ends: '13:00:00' }],
  };
  const absence: Absence = { id: 9, starts: '2026-11-05T00:00:00-04:00', ends: '2026-11-07T00:00:00-04:00', reason: 'Viaje' };
  const week: Week = { timezone: 'America/La_Paz', shifts: [shift], availability: [], absences: [absence] };

  beforeEach(() => {
    api = jasmine.createSpyObj<AgendaApiService>('AgendaApiService', ['week', 'saveShift', 'createShifts', 'saveAbsence', 'deleteAbsence']);
    api.week.and.returnValue(of(week));
    api.createShifts.and.returnValue(of([]));
    api.saveShift.and.returnValue(of(shift));
    api.saveAbsence.and.returnValue(of({}));
    api.deleteAbsence.and.returnValue(of({}));
    TestBed.configureTestingModule({
      providers: [
        ...provideTestTranslations(),
        { provide: AgendaApiService, useValue: api },
        { provide: PersonnelApiService, useValue: { list: () => of({ results: [{ id: 'p1', name: 'Ana' } as Profile], next: null }) } },
      ],
    });
    fixture = TestBed.createComponent(AgendaComponent);
    component = fixture.componentInstance;
    component.start = '2026-11-02';
    component.selection.setValue('p1');
    component.week = week;
    fixture.detectChanges();
  });

  it('selects several days with shortcuts and summarizes them (AC-07)', () => {
    component.edit();
    expect(component.shift.controls.days.invalid).toBeTrue();
    component.toggleDay(0);
    component.toggleDay(1);
    expect(component.shift.controls.days.value).toEqual([0, 1]);
    component.pickDays([0, 1, 2, 3, 4]);
    component.shift.patchValue({ starts: '08:00', ends: '20:00' });
    expect(component.shiftSummary).toContain('Lun, Mar, Mié, Jue, Vie');
    component.pickDays([]);
    component.shift.patchValue({ starts: '08:00', ends: '20:00' });
    expect(component.shift.invalid).toBeTrue();
  });

  it('creates one request with all the chosen days (AC-07)', () => {
    component.edit();
    component.pickDays([0, 1, 2]);
    component.shift.patchValue({ starts: '08:00', ends: '20:00' });
    component.saveShift(dialog);
    expect(api.createShifts).toHaveBeenCalledWith('p1', {
      days: [0, 1, 2], starts: '08:00', ends: '20:00', valid_from: '2026-11-02', valid_until: '2026-11-08', breaks: [],
    });
  });

  it('computes the validity of each repetition option (AC-08)', () => {
    component.edit();
    component.shift.controls.repeat.setValue('month');
    component.applyRepeat();
    expect(component.shift.getRawValue().valid_until).toBe('2026-11-30');
    component.shift.controls.repeat.setValue('week');
    component.applyRepeat();
    expect(component.shift.getRawValue().valid_until).toBe('2026-11-08');
  });

  it('edits a shift on a single day with PUT', () => {
    component.edit(shift);
    component.toggleDay(4);
    expect(component.shift.controls.days.value).toEqual([4]);
    component.saveShift(dialog);
    expect(api.saveShift).toHaveBeenCalledWith('p1', jasmine.objectContaining({ day: 4 }), 5);
  });

  it('copies a shift to other days without enabling the original day (AC-11)', () => {
    component.edit(shift, true);
    expect(component.editId).toBeUndefined();
    expect(component.shift.controls.days.value).toEqual([]);
    expect(component.dayDisabled(2)).toBeTrue();
    expect(component.dayDisabled(3)).toBeFalse();
    expect(component.shift.getRawValue()).toEqual(jasmine.objectContaining({ starts: '08:00', ends: '20:00', valid_until: '2026-11-08' }));
    expect(component.shift.controls.breaks.length).toBe(1);
  });

  it('shows edit and delete actions on each absence (AC-09)', () => {
    const buttons = Array.from(fixture.nativeElement.querySelectorAll('li button')) as HTMLButtonElement[];
    const labels = buttons.map(button => button.textContent?.trim());
    expect(labels.filter(label => label === 'Editar').length).toBeGreaterThan(0);
    expect(labels.filter(label => label === 'Eliminar').length).toBeGreaterThan(0);
  });

  it('loads an absence, saves it with PUT and deletes it after confirming (AC-09, AC-10)', () => {
    component.editAbsence(absence);
    expect(component.absence.getRawValue()).toEqual({ allDay: true, starts: '2026-11-05', ends: '2026-11-06', reason: 'Viaje' });
    expect(component.absenceDuration).toBe('Duración: 2 días');
    component.saveAbsence(dialog);
    expect(api.saveAbsence).toHaveBeenCalledWith(
      'p1', { starts: '2026-11-05T00:00', ends: '2026-11-07T00:00', reason: 'Viaje' }, 9,
    );
    component.editAbsence(absence, true);
    expect(component.confirmDelete).toBeTrue();
    component.removeAbsence(dialog);
    expect(api.deleteAbsence).toHaveBeenCalledWith('p1', 9);
  });

  it('keeps timed absences with date and time and creates new ones with POST', () => {
    component.editAbsence();
    component.absence.patchValue({ starts: '2026-11-05T07:00', ends: '2026-11-05T09:30', reason: 'Curso' });
    expect(component.absenceDuration).toBe('Duración: 2 h 30 min');
    component.saveAbsence(dialog);
    expect(api.saveAbsence).toHaveBeenCalledWith('p1', { starts: '2026-11-05T07:00', ends: '2026-11-05T09:30', reason: 'Curso' }, undefined);
  });
});
