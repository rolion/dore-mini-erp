import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { TranslateService } from '@ngx-translate/core';
import { AppointmentFailure } from '../models/appointment';
import {
  AppointmentsApiService, formatDateTime, toFailure, toLocalInput, toServerDateTime,
} from './appointments-api.service';
import { provideTestTranslations } from '../../../core/i18n/testing';

describe('AppointmentsApiService', () => {
  let api: AppointmentsApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(AppointmentsApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('sends only the filters that have a value', () => {
    api.list({ from: '2026-11-02', status: '', search: 'ana', page: 2 }).subscribe();
    const request = http.expectOne(req => req.url.endsWith('/agenda/appointments/'));
    expect(request.request.params.get('from')).toBe('2026-11-02');
    expect(request.request.params.get('search')).toBe('ana');
    expect(request.request.params.get('page')).toBe('2');
    expect(request.request.params.has('status')).toBeFalse();
    request.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('posts actions with a dashed path', () => {
    api.act('abc', 'no_show').subscribe();
    const request = http.expectOne(req => req.url.endsWith('/agenda/appointments/abc/no-show/'));
    expect(request.request.method).toBe('POST');
    request.flush({});
  });

  it('maps a 409 to a conflict failure with the message translated from its code', () => {
    let failure: AppointmentFailure | undefined;
    api.create({
      professional_id: 'p', customer_id: 'c', service_id: 's', starts: '2030-01-07T09:00:00-04:00',
      duration_minutes: 30, notes: '',
    }).subscribe({ error: (error: AppointmentFailure) => failure = error });
    http.expectOne(req => req.method === 'POST').flush({ detail: 'Ocupado', code: 'schedule_conflict' },
      { status: 409, statusText: 'Conflict' });
    expect(failure).toEqual({ message: 'El profesional ya tiene una cita en ese horario.', fields: {}, conflict: true });
  });

  it('maps 400 field errors and generic failures', () => {
    const invalid = new HttpErrorResponse({ status: 400, error: { starts: ['Fuera de turno'] } });
    expect(toFailure(invalid).fields['starts']).toBe('Fuera de turno');
    expect(toFailure(new HttpErrorResponse({ status: 0 })).message).toContain('servidor');
    expect(toFailure(new HttpErrorResponse({ status: 403 })).message).toContain('permiso');
    expect(toFailure('x').conflict).toBeFalse();
  });

  it('translates server errors by code into the selected language and keeps unknown ones', async () => {
    const invalid = new HttpErrorResponse({
      status: 400, error: { starts: ['El horario queda fuera.'], reason: ['Otro'], codes: { starts: 'outside_availability', reason: 'desconocido' } },
    });
    expect(toFailure(invalid).fields['starts']).toContain('fuera del turno');
    await TestBed.inject(TranslateService).use('en').toPromise();
    expect(toFailure(invalid).fields['starts']).toContain('outside');
    expect(toFailure(invalid).fields['reason']).toBe('Otro');
    expect(toFailure(invalid).fields['codes']).toBeUndefined();
    const conflict = new HttpErrorResponse({ status: 409, error: { detail: 'El profesional ya tiene una cita en ese horario.', code: 'schedule_conflict' } });
    expect(toFailure(conflict).message).toBe('The professional already has an appointment at that time.');
    await TestBed.inject(TranslateService).use('pt').toPromise();
    expect(toFailure(conflict).message).toContain('já tem um agendamento');
  });

  it('formats Bolivia date times', () => {
    expect(toServerDateTime('2030-01-07T09:00')).toBe('2030-01-07T09:00:00-04:00');
    expect(toLocalInput('2030-01-07T09:00:00-04:00')).toBe('2030-01-07T09:00');
    expect(formatDateTime('2030-01-07T09:30:00-04:00')).toBe('07/01/2030 09:30');
  });
});
