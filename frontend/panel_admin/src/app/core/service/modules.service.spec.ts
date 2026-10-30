import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../environments/environment';
import { ModuleDto, ModulesApiError } from '../models/module';
import { ModulesService } from './modules.service';

const URL = `${environment.apiUrl}/modules/`;

function dto(key: string, enabled: boolean, extra: Partial<ModuleDto> = {}): ModuleDto {
  return {
    key,
    name: key,
    description: '',
    is_base: key === 'catalog' || key === 'access',
    enabled,
    requires: [],
    optional: [],
    missing_requires: [],
    ...extra,
  };
}

describe('ModulesService', () => {
  let service: ModulesService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(ModulesService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('publishes the enabled keys of the company (AC-04)', () => {
    service.load().subscribe();
    http.expectOne(URL).flush([dto('catalog', true), dto('inventory', true), dto('purchases', false)]);
    expect(Array.from(service.enabledKeysValue ?? [])).toEqual(['catalog', 'inventory']);
  });

  it('falls back to base modules only when loading fails (EDGE-05)', () => {
    let error: ModulesApiError | undefined;
    service.load().subscribe({ error: (err: ModulesApiError) => (error = err) });
    http.expectOne(URL).flush({}, { status: 500, statusText: 'Server Error' });
    expect(error?.message).toContain('No se pudieron cargar');
    expect(Array.from(service.enabledKeysValue ?? []).sort()).toEqual(['access', 'catalog']);
  });

  it('exposes the missing dependency names of a rejected enable (AC-03)', () => {
    let error: ModulesApiError | undefined;
    service.enable('purchases').subscribe({ error: (err: ModulesApiError) => (error = err) });
    http
      .expectOne(`${URL}purchases/enable/`)
      .flush({ detail: 'Faltan módulos por habilitar: Gastos.', missing: ['Gastos'] }, { status: 409, statusText: 'Conflict' });
    expect(error?.status).toBe(409);
    expect(error?.names).toEqual(['Gastos']);
    expect(error?.message).toContain('Gastos');
  });

  it('shares one request between simultaneous loads (REV-01)', () => {
    service.load().subscribe();
    service.loadQuietly().subscribe();
    http.expectOne(URL).flush([dto('catalog', true)]);
    service.load().subscribe();
    http.expectOne(URL).flush([dto('catalog', true)]);
  });

  it('forgets the state on reset', () => {
    service.load().subscribe();
    http.expectOne(URL).flush([dto('catalog', true)]);
    service.reset();
    expect(service.enabledKeysValue).toBeNull();
  });

  it('maps capabilities, adoption date and blockers, defaulting when absent (API-01)', () => {
    service.load().subscribe();
    http.expectOne(URL).flush([
      dto('catalog', true),
      dto('costing', true, {
        capabilities: [{ key: 'inventory.valuation', label: 'Valoración de Inventario', available: true }],
        adopted_at: '2026-10-30T12:00:00+00:00',
        disable_blockers: [{ code: 'open_costs', message: 'Costos sin cerrar', resolution: 'Ciérralos' }],
      }),
    ]);
    let costing;
    service.modules$.subscribe((m) => (costing = m?.find((x) => x.key === 'costing')));
    expect(costing).toEqual(
      jasmine.objectContaining({
        adoptedAt: '2026-10-30T12:00:00+00:00',
        missingCapabilities: [],
        disableBlockers: [{ code: 'open_costs', message: 'Costos sin cerrar', resolution: 'Ciérralos' }],
      }),
    );
  });

  it('exposes the missing capability labels of a rejected enable (API-02)', () => {
    let error: ModulesApiError | undefined;
    service.enable('costing').subscribe({ error: (err: ModulesApiError) => (error = err) });
    http
      .expectOne(`${URL}costing/enable/`)
      .flush(
        { detail: 'Falta la capacidad: Valoración de Inventario.', missing_capabilities: ['Valoración de Inventario'] },
        { status: 409, statusText: 'Conflict' },
      );
    expect(error?.names).toEqual(['Valoración de Inventario']);
  });
});
