import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { Customer, CustomersApiService } from '../../customers';
import { CUSTOMER_SEARCH_PAGE_SIZE, CustomerOptionsService } from './customer-options.service';

const CUSTOMER: Customer = {
  id: 'c-1',
  name: 'Ana Pérez',
  phone: '+59176543210',
  email: 'ana@example.com',
  notes: '',
  active: true,
  createdAt: '',
  updatedAt: '',
};

describe('CustomerOptionsService', () => {
  let service: CustomerOptionsService;
  let api: jasmine.SpyObj<CustomersApiService>;

  beforeEach(() => {
    api = jasmine.createSpyObj<CustomersApiService>('CustomersApiService', ['list']);
    TestBed.configureTestingModule({ providers: [{ provide: CustomersApiService, useValue: api }] });
    service = TestBed.inject(CustomerOptionsService);
  });

  it('searches only active customers by the trimmed term and keeps id and name (AC-24)', () => {
    api.list.and.returnValue(of({ count: 1, next: null, previous: null, results: [CUSTOMER] }));
    let result: unknown;
    service.search('  ana ').subscribe((options) => (result = options));
    expect(api.list).toHaveBeenCalledOnceWith({ search: 'ana', active: true, pageSize: CUSTOMER_SEARCH_PAGE_SIZE });
    expect(result).toEqual([{ id: 'c-1', name: 'Ana Pérez' }]);
  });

  it('tolerates a null or undefined term, as ng-select emits when an option is chosen (EDGE-14, REV-02)', () => {
    api.list.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    for (const term of [null, undefined]) {
      let result: unknown;
      expect(() => service.search(term).subscribe((options) => (result = options))).not.toThrow();
      expect(result).toEqual([]);
      expect(api.list.calls.mostRecent().args[0]).toEqual({
        search: '', active: true, pageSize: CUSTOMER_SEARCH_PAGE_SIZE,
      });
    }
  });

  it('turns a synchronous failure of the request into an empty list instead of killing the stream (EDGE-14)', () => {
    api.list.and.throwError('boom');
    let result: unknown;
    service.search('x').subscribe((options) => (result = options));
    expect(result).toEqual([]);
  });

  it('returns an empty list when the search fails', () => {
    api.list.and.returnValue(throwError(() => new Error('red')));
    let result: unknown;
    service.search('x').subscribe((options) => (result = options));
    expect(result).toEqual([]);
  });
});
