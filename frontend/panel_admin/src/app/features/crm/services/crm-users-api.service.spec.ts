import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../../environments/environment';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { CrmApiError } from '../models/board';
import { CrmOwner } from '../models/opportunity';
import { CrmUsersApiService } from './crm-users-api.service';

describe('CrmUsersApiService', () => {
  let api: CrmUsersApiService;
  let http: HttpTestingController;
  const url = `${environment.apiUrl}/crm/users/`;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(CrmUsersApiService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('lists the company users, with an optional search text', () => {
    let users: CrmOwner[] | undefined;
    api.list().subscribe((u) => (users = u));
    const first = http.expectOne((r) => r.url === url);
    expect(first.request.params.has('search')).toBeFalse();
    first.flush([{ id: 1, name: 'Ana (ana)' }]);
    expect(users).toEqual([{ id: 1, name: 'Ana (ana)' }]);

    api.list(' ana ').subscribe();
    const second = http.expectOne((r) => r.url === url);
    expect(second.request.params.get('search')).toBe('ana');
    second.flush([]);
  });

  it('turns HTTP errors into CrmApiError', () => {
    let error: CrmApiError | undefined;
    api.list().subscribe({ error: (e: CrmApiError) => (error = e) });
    http.expectOne((r) => r.url === url).flush({ detail: 'No autorizado.' }, { status: 403, statusText: 'Forbidden' });
    expect(error?.status).toBe(403);
  });
});
