import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ServiceApiError, ServiceDto } from '../models/service';
import { ServicesApiService } from './services-api.service';

export const serviceDto: ServiceDto = { id: 'service-1', name: 'Consulta', code: 'CON-01', description: '',
  base_price: '120.00', duration_minutes: 30, specialty_id: null, specialty_name: null, active: true,
  created_at: '2026-11-02T12:00:00Z', updated_at: '2026-11-02T12:00:00Z' };

describe('ServicesApiService', () => {
  let api: ServicesApiService;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(ServicesApiService); http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  it('normalizes codes in requests and maps decimal strings without numeric conversion', () => {
    api.create({ name: 'Consulta', code: ' con-01 ', description: '', basePrice: '120.00', durationMinutes: 30, specialtyId: null })
      .subscribe(service => { expect(service.basePrice).toBe('120.00'); expect(service.durationMinutes).toBe(30); });
    const req = http.expectOne('/api/services/');
    expect(req.request.method).toBe('POST');
    expect(req.request.body.code).toBe('CON-01'); expect(req.request.body.base_price).toBe('120.00');
    expect(req.request.body.specialty_id).toBeNull(); req.flush(serviceDto);
  });
  it('sends active-only selection and pagination to the server', () => {
    api.list({ active: true, search: 'Consulta', page: 2, pageSize: 20 }).subscribe(page => expect(page.results[0].code).toBe('CON-01'));
    const req = http.expectOne(request => request.url === '/api/services/' && request.params.get('active') === 'true');
    expect(req.request.params.get('page')).toBe('2'); expect(req.request.params.get('search')).toBe('Consulta');
    req.flush({ count: 21, next: null, previous: null, results: [serviceDto] });
  });
  it('maps duplicate and duration errors to the form', () => {
    api.update('service-1', { code: 'con-01' }).subscribe({ error: (error: ServiceApiError) => {
      expect(error.fields.code).toBe('Duplicado'); expect(error.fields.durationMinutes).toBe('Mayor que cero');
    } });
    const req = http.expectOne('/api/services/service-1/'); expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ code: 'CON-01' });
    req.flush({ code: ['Duplicado'], duration_minutes: ['Mayor que cero'] }, { status: 400, statusText: 'Bad Request' });
  });
  it('uses explicit state actions and reports forbidden access', () => {
    api.setActive('service-1', false).subscribe({ error: (error: ServiceApiError) => expect(error.message).toContain('permiso') });
    const req = http.expectOne('/api/services/service-1/deactivate/'); expect(req.request.method).toBe('POST');
    req.flush({}, { status: 403, statusText: 'Forbidden' });
  });
  it('identifies a vanished page so the list can recover without hiding other errors', () => {
    api.list({ page: 2 }).subscribe({ error: (error: ServiceApiError) => expect(error.invalidPage).toBeTrue() });
    const req = http.expectOne(request => request.url === '/api/services/');
    req.flush({ page: ['La página ya no está disponible.'] }, { status: 400, statusText: 'Bad Request' });
  });
});
