import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../../environments/environment';
import { AgendaApiService } from './agenda-api.service';

describe('AgendaApiService', () => {
  let service: AgendaApiService;
  let http: HttpTestingController;
  const body = { day: 0, starts: '09:00', ends: '12:00', valid_from: '2026-11-02', valid_until: '2026-11-08', breaks: [] };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(AgendaApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('requests the week of a professional', () => {
    service.week('7', '2026-11-02').subscribe();
    const req = http.expectOne(r => r.url === `${environment.apiUrl}/agenda/7/week/`);
    expect(req.request.params.get('start')).toBe('2026-11-02');
    req.flush({});
  });

  it('creates a shift with POST and edits it with PUT', () => {
    service.saveShift('7', body).subscribe();
    expect(http.expectOne(`${environment.apiUrl}/agenda/7/shifts/`).request.method).toBe('POST');
    service.saveShift('7', body, 3).subscribe();
    expect(http.expectOne(`${environment.apiUrl}/agenda/7/shifts/3/`).request.method).toBe('PUT');
  });

  it('registers an absence', () => {
    service.saveAbsence('7', { starts: 'a', ends: 'b', reason: 'Permiso' }).subscribe();
    expect(http.expectOne(`${environment.apiUrl}/agenda/7/absences/`).request.method).toBe('POST');
  });
});
