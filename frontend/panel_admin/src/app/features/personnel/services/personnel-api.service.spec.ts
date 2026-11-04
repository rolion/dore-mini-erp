import { provideTestTranslations } from '../../../core/i18n/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../../environments/environment';
import { PersonnelApiService } from './personnel-api.service';

describe('PersonnelApiService', () => {
  let service: PersonnelApiService;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(PersonnelApiService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  it('creates a professional without user or specialties (AC-01)', () => {
    service.save('professionals', { name: 'Ana' }, null).subscribe();
    const request = http.expectOne(`${environment.apiUrl}/professionals/`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ name: 'Ana' });
    request.flush({ id: 'p', name: 'Ana' });
  });
  it('sends explicit null to unlink without changing permissions (AC-03)', () => {
    service.save('professionals', { name: 'Ana', user_id: null }, 'p').subscribe();
    const request = http.expectOne(`${environment.apiUrl}/professionals/p/`);
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body.user_id).toBeNull();
    expect(request.request.body.role).toBeUndefined();
    request.flush({ id: 'p' });
  });
  it('sends server-side filters and pagination (AC-04)', () => {
    service.list('professionals', { search: 'Ana', active: false, specialty_id: 's', page: 2 }).subscribe();
    const request = http.expectOne(req => req.url === `${environment.apiUrl}/professionals/`);
    expect(request.request.params.get('active')).toBe('false');
    expect(request.request.params.get('specialty_id')).toBe('s');
    expect(request.request.params.get('page')).toBe('2');
    request.flush({ count: 0, results: [] });
  });
  it('loads every options page rather than silently dropping specialties (AC-02)', () => {
    let names: string[] = [];
    service.specialties().subscribe(items => names = items.map(item => item.name));
    http.expectOne(req => req.params.get('page') === '1').flush({ next: 'next', results: [{ id: '1', name: 'A' }] });
    http.expectOne(req => req.params.get('page') === '2').flush({ next: null, results: [{ id: '2', name: 'B' }] });
    expect(names).toEqual(['A', 'B']);
  });
  it('looks up the current user by id (AC-03)', () => {
    service.users('', 7).subscribe();
    const request = http.expectOne(req => req.url.endsWith('/professionals/users/'));
    expect(request.request.params.get('id')).toBe('7');
    request.flush({ results: [] });
  });
});
