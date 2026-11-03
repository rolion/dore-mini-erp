import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { Subject, of, throwError } from 'rxjs';
import { CatalogService, ServiceApiError } from '../models/service';
import { ServiceFiltersState, ServicesApiService } from '../services/services-api.service';
import { PersonnelApiService } from '../../personnel/services/personnel-api.service';
import { ServiceFormComponent } from './service-form.component';
import { ServiceListComponent } from './service-list.component';
import { ServiceDetailComponent } from './service-detail.component';

const service: CatalogService = { id: 'one', name: 'Consulta', code: 'CON-01', description: '', basePrice: '120.00', durationMinutes: 30,
  specialtyId: null, specialtyName: null, active: true, createdAt: '2026-11-02T12:00:00Z', updatedAt: '2026-11-02T12:00:00Z' };

describe('ServiceFormComponent', () => {
  let api: jasmine.SpyObj<ServicesApiService>;
  let personnel: jasmine.SpyObj<PersonnelApiService>;
  beforeEach(() => {
    api = jasmine.createSpyObj<ServicesApiService>('api', ['get', 'create', 'update']);
    personnel = jasmine.createSpyObj<PersonnelApiService>('personnel', ['specialties']);
    personnel.specialties.and.returnValue(of([{ id: 'specialty-1', name: 'Ortodoncia', active: true,
      created_by: 1, updated_by: 1, created_at: '', updated_at: '' }]));
    TestBed.configureTestingModule({ imports: [ServiceFormComponent], providers: [provideRouter([]),
      { provide: ServicesApiService, useValue: api },
      { provide: PersonnelApiService, useValue: personnel },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({}) } } }] });
  });
  function validForm(component: ServiceFormComponent): void {
    component.form.patchValue({ name: 'Consulta', code: 'con-01', basePrice: '120.00', durationMinutes: 30 });
  }
  it('shows uppercase codes and selectable active specialties', () => {
    const fixture = TestBed.createComponent(ServiceFormComponent); fixture.detectChanges();
    validForm(fixture.componentInstance); fixture.detectChanges();
    expect(fixture.componentInstance.form.controls.code.value).toBe('CON-01');
    expect(fixture.componentInstance.form.controls.specialtyId.enabled).toBeTrue();
    expect(fixture.nativeElement.textContent).toContain('Ortodoncia');
    expect(fixture.componentInstance.form.valid).toBeTrue();
  });
  it('sends a selected specialty with the service', () => {
    api.create.and.returnValue(of({ ...service, specialtyId: 'specialty-1', specialtyName: 'Ortodoncia' }));
    const fixture = TestBed.createComponent(ServiceFormComponent); fixture.detectChanges();
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    validForm(fixture.componentInstance);
    fixture.componentInstance.form.controls.specialtyId.setValue('specialty-1');
    fixture.componentInstance.save();
    expect(api.create).toHaveBeenCalledWith(jasmine.objectContaining({ specialtyId: 'specialty-1' }));
    expect(navigate).toHaveBeenCalled();
  });
  it('keeps specialty optional when Personal is unavailable', () => {
    personnel.specialties.and.returnValue(throwError(() => new Error('Personal disabled')));
    const fixture = TestBed.createComponent(ServiceFormComponent); fixture.detectChanges();
    validForm(fixture.componentInstance); fixture.detectChanges();
    expect(fixture.componentInstance.form.controls.specialtyId.disabled).toBeTrue();
    expect(fixture.nativeElement.textContent).toContain('Habilita Personal');
    expect(fixture.componentInstance.form.valid).toBeTrue();
  });
  it('rejects zero/fractional duration and invalid price before sending', () => {
    const fixture = TestBed.createComponent(ServiceFormComponent); fixture.detectChanges(); const c = fixture.componentInstance;
    validForm(c);
    for (const value of [0, -1, 1.5]) { c.form.controls.durationMinutes.setValue(value); c.save(); expect(c.form.invalid).toBeTrue(); }
    c.form.controls.durationMinutes.setValue(30); c.form.controls.basePrice.setValue('1.001'); c.save();
    expect(api.create).not.toHaveBeenCalled();
  });
  it('preserves entered data and shows server field errors', () => {
    api.create.and.returnValue(throwError(() => new ServiceApiError('Revisa los datos', 400, { code: 'Duplicado' })));
    const fixture = TestBed.createComponent(ServiceFormComponent); fixture.detectChanges(); const c = fixture.componentInstance;
    validForm(c); c.form.markAsDirty(); c.save(); fixture.detectChanges();
    expect(c.form.controls.basePrice.value).toBe('120.00'); expect(c.hasUnsavedChanges()).toBeTrue();
    expect(fixture.nativeElement.textContent).toContain('Duplicado'); expect(c.saving).toBeFalse();
  });
  it('prevents double submission and clears dirty state only on success', () => {
    const response = new Subject<CatalogService>(); api.create.and.returnValue(response);
    const fixture = TestBed.createComponent(ServiceFormComponent); fixture.detectChanges(); const c = fixture.componentInstance;
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    validForm(c); c.form.markAsDirty(); c.save(); c.save(); expect(api.create).toHaveBeenCalledTimes(1);
    response.next(service); response.complete(); expect(c.hasUnsavedChanges()).toBeFalse(); expect(navigate).toHaveBeenCalled();
  });
  it('blocks browser unload with unsaved entries', () => {
    const fixture = TestBed.createComponent(ServiceFormComponent); const c = fixture.componentInstance;
    c.form.markAsDirty(); const event = new Event('beforeunload', { cancelable: true }) as BeforeUnloadEvent;
    c.beforeUnload(event); expect(event.defaultPrevented).toBeTrue();
  });
});

describe('ServiceListComponent', () => {
  let api: jasmine.SpyObj<ServicesApiService>;
  let personnel: jasmine.SpyObj<PersonnelApiService>;
  beforeEach(() => {
    api = jasmine.createSpyObj<ServicesApiService>('api', ['list']);
    api.list.and.returnValue(of({ count: 1, next: null, previous: null, results: [service] }));
    personnel = jasmine.createSpyObj<PersonnelApiService>('personnel', ['specialties']);
    personnel.specialties.and.returnValue(of([]));
    TestBed.configureTestingModule({ imports: [ServiceListComponent], providers: [provideRouter([]),
      { provide: ServicesApiService, useValue: api }, { provide: PersonnelApiService, useValue: personnel }] });
  });
  it('restores filters and pagination and displays formatted values', () => {
    api.list.and.returnValue(of({ count: 21, next: null, previous: null, results: [service] }));
    const state = TestBed.inject(ServiceFiltersState); state.search = 'Cons'; state.status = 'all'; state.pageIndex = 1;
    const fixture = TestBed.createComponent(ServiceListComponent); fixture.detectChanges();
    expect(api.list).toHaveBeenCalledWith({ search: 'Cons', active: undefined, page: 2, pageSize: 20 });
    expect(fixture.componentInstance.rows[0].durationMinutes).toBe(30);
    expect(fixture.nativeElement.textContent).toContain('Sin especialidad');
  });
  it('keeps the restored page while the table initializes with an empty loading state', () => {
    const pending = new Subject<{ count: number; next: null; previous: null; results: CatalogService[] }>();
    api.list.and.returnValue(pending);
    const state = TestBed.inject(ServiceFiltersState); state.pageIndex = 1;
    const fixture = TestBed.createComponent(ServiceListComponent); fixture.detectChanges();
    fixture.componentInstance.onPage({ offset: 0 }); expect(state.pageIndex).toBe(1);
    pending.next({ count: 21, next: null, previous: null, results: [service] });
    pending.complete(); fixture.detectChanges(); expect(state.pageIndex).toBe(1);
  });
  it('searches on the server and resets pagination', fakeAsync(() => {
    const fixture = TestBed.createComponent(ServiceListComponent); fixture.detectChanges();
    fixture.componentInstance.search.setValue('Limpieza'); tick(301);
    expect(api.list).toHaveBeenCalledWith({ search: 'Limpieza', active: true, page: 1, pageSize: 20 });
    fixture.destroy();
  }));
  it('filters by specialty and keeps it in the saved list state', () => {
    const fixture = TestBed.createComponent(ServiceListComponent); fixture.detectChanges();
    fixture.componentInstance.specialty.setValue('specialty-1');
    expect(TestBed.inject(ServiceFiltersState).specialtyId).toBe('specialty-1');
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ specialtyId: 'specialty-1', page: 1 }));
  });
  it('recovers a valid page after the last active service on a saved page is deactivated', () => {
    const state = TestBed.inject(ServiceFiltersState); state.pageIndex = 1;
    api.list.and.returnValues(of({ count: 21, next: null, previous: null, results: [service] }),
      throwError(() => new ServiceApiError('Página no disponible', 400, {}, true)),
      of({ count: 20, next: null, previous: null, results: [{ ...service, id: 'another' }] }));
    const fixture = TestBed.createComponent(ServiceListComponent); fixture.detectChanges();
    fixture.componentInstance.onUpdated({ ...service, active: false }); fixture.detectChanges();
    expect(state.pageIndex).toBe(0); expect(fixture.componentInstance.error).toBe('');
    expect(fixture.componentInstance.rows[0].id).toBe('another');
    expect(api.list).toHaveBeenCalledWith({ search: '', active: true, page: 1, pageSize: 20 });
  });
  it('shows errors and can retry without displaying stale results', () => {
    api.list.and.returnValue(throwError(() => new ServiceApiError('Sin conexión', 0)));
    const fixture = TestBed.createComponent(ServiceListComponent); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Sin conexión'); expect(fixture.componentInstance.rows).toEqual([]);
    api.list.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    fixture.componentInstance.reload(); fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('Aún no hay servicios');
  });
});

describe('ServiceDetailComponent', () => {
  it('shows price, duration, inactive state and a preserved service history', () => {
    const api = jasmine.createSpyObj<ServicesApiService>('api', ['get']); api.get.and.returnValue(of({ ...service, active: false }));
    TestBed.configureTestingModule({ imports: [ServiceDetailComponent], providers: [provideRouter([]),
      { provide: ServicesApiService, useValue: api }, { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'one' }) } } }] });
    const fixture = TestBed.createComponent(ServiceDetailComponent); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Bs 120.00'); expect(fixture.nativeElement.textContent).toContain('30 min');
    expect(fixture.nativeElement.textContent).toContain('Inactivo'); expect(api.get).toHaveBeenCalledWith('one');
  });
});
