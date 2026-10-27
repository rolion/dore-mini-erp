import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { InventoryApiError } from '../models/api-error';
import { UnitsApiService } from './units-api.service';
import { WarehousesApiService } from './warehouses-api.service';

const UNIT_DTO = { id: 'u-1', name: 'Kilogramo', abbreviation: 'kg', allows_fractions: true, active: true, in_use: false };
const WAREHOUSE_DTO = { id: 'w-1', name: 'Principal', description: '', active: true, is_default: true };

describe('Inventory API services', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  describe('UnitsApiService', () => {
    it('lists units with filters and maps them (AC-07)', () => {
      let result: unknown;
      TestBed.inject(UnitsApiService)
        .list({ search: 'kil', active: true, pageSize: 100 })
        .subscribe((page) => (result = page.results[0]));
      const req = http.expectOne((r) => r.url.endsWith('/units/'));
      expect(req.request.params.get('search')).toBe('kil');
      expect(req.request.params.get('active')).toBe('true');
      expect(req.request.params.get('page_size')).toBe('100');
      req.flush({ count: 1, next: null, previous: null, results: [UNIT_DTO] });
      expect(result).toEqual({ id: 'u-1', name: 'Kilogramo', abbreviation: 'kg', allowsFractions: true, active: true, inUse: false });
    });

    it('sends snake_case on create (AC-07)', () => {
      TestBed.inject(UnitsApiService).create({ name: 'Litro', abbreviation: 'l', allowsFractions: true }).subscribe();
      const req = http.expectOne((r) => r.url.endsWith('/units/'));
      expect(req.request.body).toEqual({ name: 'Litro', abbreviation: 'l', allows_fractions: true });
      req.flush(UNIT_DTO);
    });

    it('maps 400 field errors and 409 with code (AC-07)', () => {
      const service = TestBed.inject(UnitsApiService);
      const errors: InventoryApiError[] = [];
      service.create({ name: '', abbreviation: '', allowsFractions: false }).subscribe({ error: (e) => errors.push(e) });
      http.expectOne((r) => r.url.endsWith('/units/')).flush({ name: ['Obligatorio'] }, { status: 400, statusText: 'Bad Request' });
      service.update('u-1', { name: 'x' }).subscribe({ error: (e) => errors.push(e) });
      http.expectOne((r) => r.url.endsWith('/units/u-1/')).flush(
        { detail: 'Esta unidad ya está asignada a productos; solo se puede activar o desactivar.', code: 'unit_in_use' },
        { status: 409, statusText: 'Conflict' },
      );
      expect(errors[0].fieldErrors['name']).toEqual(['Obligatorio']);
      expect(errors[1].code).toBe('unit_in_use');
      expect(errors[1].message).toContain('solo se puede activar o desactivar');
    });
  });

  describe('WarehousesApiService', () => {
    it('maps warehouses and posts make-default (AC-08)', () => {
      const service = TestBed.inject(WarehousesApiService);
      let isDefault: boolean | undefined;
      service.makeDefault('w-1').subscribe((w) => (isDefault = w.isDefault));
      const req = http.expectOne((r) => r.url.endsWith('/warehouses/w-1/make-default/'));
      expect(req.request.method).toBe('POST');
      req.flush(WAREHOUSE_DTO);
      expect(isDefault).toBeTrue();
    });

    it('sends is_default on create and surfaces the 409 reason (AC-09)', () => {
      const service = TestBed.inject(WarehousesApiService);
      service.create({ name: 'Bodega', description: '', isDefault: true }).subscribe();
      const create = http.expectOne((r) => r.url.endsWith('/warehouses/'));
      expect(create.request.body).toEqual({ name: 'Bodega', description: '', is_default: true });
      create.flush(WAREHOUSE_DTO);

      let error: InventoryApiError | undefined;
      service.deactivate('w-2').subscribe({ error: (e) => (error = e) });
      http.expectOne((r) => r.url.endsWith('/warehouses/w-2/deactivate/')).flush(
        { detail: 'No se puede desactivar: el almacén tiene saldo distinto de cero.', code: 'warehouse_has_stock' },
        { status: 409, statusText: 'Conflict' },
      );
      expect(error?.code).toBe('warehouse_has_stock');
    });

    it('reports network errors', () => {
      let error: InventoryApiError | undefined;
      TestBed.inject(WarehousesApiService).list().subscribe({ error: (e) => (error = e) });
      http.expectOne((r) => r.url.endsWith('/warehouses/')).error(new ProgressEvent('error'));
      expect(error?.status).toBe(0);
    });
  });
});
