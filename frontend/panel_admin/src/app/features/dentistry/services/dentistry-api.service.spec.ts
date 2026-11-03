import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { DentistryApiService } from './dentistry-api.service';
import { makePatient } from '../testing/patient-fixtures';

describe('DentistryApiService contracts', () => {
  let api: DentistryApiService;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(DentistryApiService); http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  it('sends identity only when creating a profile', () => {
    api.create('c-1').subscribe(value => expect(value.id).toBe('c-1'));
    const request = http.expectOne('/api/dentistry/patients/');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ customer_id: 'c-1' });
    request.flush(makePatient());
  });
  it('passes server-side search, status and pagination', () => {
    api.list('Ana', 'false', 2).subscribe();
    const request = http.expectOne(req => req.url === '/api/dentistry/patients/');
    expect(request.request.params.get('search')).toBe('Ana');
    expect(request.request.params.get('active')).toBe('false');
    expect(request.request.params.get('page')).toBe('2');
    request.flush({ count: 0, results: [], next: null, previous: null });
  });
  it('writes administrative data to Customers, never the clinical endpoint', () => {
    const input = { birth_date: null, responsible_name: '', responsible_phone: '' };
    api.demographics('c-1', input).subscribe();
    const request = http.expectOne('/api/customers/c-1/demographics/');
    expect(request.request.method).toBe('PATCH'); expect(request.request.body).toEqual(input);
    request.flush(input);
  });
  it('uses separate paginated histories', () => {
    api.history('c-1', true, 2).subscribe();
    const clinical = http.expectOne('/api/dentistry/patients/c-1/history/?page=2');
    expect(clinical.request.method).toBe('GET'); clinical.flush({ results: [] });
    api.history('c-1', false, 1).subscribe();
    const administrative = http.expectOne('/api/customers/c-1/demographics/history/?page=1');
    expect(administrative.request.method).toBe('GET'); administrative.flush({ results: [] });
  });
  it('uses archive/activate actions and checks server capabilities', () => {
    api.setActive('c-1', false).subscribe(); http.expectOne('/api/dentistry/patients/c-1/archive/').flush(makePatient());
    api.setActive('c-1', true).subscribe(); http.expectOne('/api/dentistry/patients/c-1/activate/').flush(makePatient());
    api.capabilities().subscribe(value => expect(value.clinical_access).toBeTrue());
    http.expectOne('/api/dentistry/capabilities/').flush({ clinical_access: true });
  });
});
