import { provideTestTranslations } from '../../../core/i18n/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';
import { CustomersApiService } from '../../customers/services/customers-api.service';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { Customer, CustomerApiError } from '../../customers/models/customer';
import { DentistryApiService } from '../services/dentistry-api.service';
import { Patient } from '../models/patient';
import { makePatient, EMPTY_HISTORY } from '../testing/patient-fixtures';
import { PatientCreateComponent } from './patient-create.component';
describe('PatientCreateComponent', () => {
  const customer: Customer = { id: 'c-1', name: 'Ana', phone: '', email: '', notes: '', active: true, createdAt: '', updatedAt: '' };
  let api: jasmine.SpyObj<DentistryApiService>;
  let customers: jasmine.SpyObj<CustomersApiService>;
  beforeEach(async () => {
    api = jasmine.createSpyObj<DentistryApiService>('api', ['get', 'create']);
    customers = jasmine.createSpyObj<CustomersApiService>('customers', ['list']);
    customers.list.and.returnValue(of({ ...EMPTY_HISTORY, results: [customer] }));
    await TestBed.configureTestingModule({ imports: [PatientCreateComponent], providers: [...provideTestTranslations(), provideRouter([]),
      { provide: DentistryApiService, useValue: api }, { provide: CustomersApiService, useValue: customers },
      { provide: NgbActiveModal, useValue: { close: () => undefined, dismiss: () => undefined } },
      { provide: ToastrService, useValue: {} },
    ] }).compileComponents();
  });
  it('opens an existing profile without allowing duplicate creation', () => {
    api.get.and.returnValue(of(makePatient()));
    const fixture = TestBed.createComponent(PatientCreateComponent); fixture.detectChanges();
    fixture.componentInstance.select(customer); fixture.componentInstance.create(); fixture.detectChanges();
    expect(api.create).not.toHaveBeenCalled();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Ana ya es paciente.');
    expect(fixture.nativeElement.querySelector('.alert-danger')).toBeNull();
    expect((fixture.nativeElement as HTMLElement).querySelector('.modal-footer .btn-primary')?.textContent).toContain('Abrir ficha');
  });
  it('explains why the primary action is disabled and uses patient wording (AC-01, AC-06)', () => {
    api.get.and.returnValue(throwError(() => new HttpErrorResponse({ status: 404 })));
    const fixture = TestBed.createComponent(PatientCreateComponent); fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.textContent).toContain('Busca a la persona entre tus clientes');
    expect(root.textContent).toContain('Elige o registra a una persona');
    expect(root.textContent).not.toContain('ficha clínica');
    expect((root.querySelector('.modal-footer .btn-primary') as HTMLButtonElement).textContent).toContain('Crear paciente');
    expect((root.querySelector('.modal-footer .btn-primary') as HTMLButtonElement).disabled).toBeTrue();
  });
  it('creates the profile right after registering a new customer, without another click (AC-03)', () => {
    const fixture = TestBed.createComponent(PatientCreateComponent); fixture.detectChanges();
    const component = fixture.componentInstance; component.createCustomer();
    api.create.and.returnValue(of(makePatient()));
    component.customerCreated(customer);
    expect(api.get).not.toHaveBeenCalled();
    expect(api.create).toHaveBeenCalledOnceWith('c-1');
    expect(component.opening).toBeFalse();
  });
  it('keeps the new customer and retries only the profile when it fails (AC-04)', () => {
    const fixture = TestBed.createComponent(PatientCreateComponent); fixture.detectChanges();
    const component = fixture.componentInstance;
    api.create.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500 })));
    component.customerCreated(customer); fixture.detectChanges();
    expect(component.selected).toEqual(customer); expect(component.profileFailed).toBeTrue();
    expect(fixture.nativeElement.textContent).toContain('Se registró a Ana como cliente, pero no se pudo crear su ficha.');
    expect(customers.list).toHaveBeenCalledTimes(1);
    api.create.and.returnValue(of(makePatient()));
    component.create();
    expect(api.create).toHaveBeenCalledTimes(2);
  });
  it('passes patient labels to the embedded quick-create form (AC-02)', () => {
    const fixture = TestBed.createComponent(PatientCreateComponent); fixture.detectChanges();
    fixture.componentInstance.createCustomer(); fixture.detectChanges();
    const form = fixture.nativeElement as HTMLElement;
    expect(form.querySelector('button[type="submit"]')?.textContent).toContain('Registrar paciente');
    expect(form.textContent).toContain('Volver a buscar');
  });
  it('prevents duplicate submits and links the winner after a concurrent conflict', () => {
    api.get.and.returnValue(throwError(() => new HttpErrorResponse({ status: 404 })));
    const fixture = TestBed.createComponent(PatientCreateComponent); fixture.detectChanges();
    const component = fixture.componentInstance; component.select(customer);
    const pending = new Subject<Patient>(); api.create.and.returnValue(pending);
    component.create(); component.create(); expect(api.create).toHaveBeenCalledTimes(1);
    pending.error(new HttpErrorResponse({ status: 409, error: { detail: 'Perfil existente' } }));
    expect(component.existingId).toBe('c-1'); expect(component.selected).toEqual(customer);
  });
  it('renders the existing quick-create form inside the patient modal', () => {
    api.get.and.returnValue(throwError(() => new HttpErrorResponse({ status: 404 })));
    const fixture = TestBed.createComponent(PatientCreateComponent); fixture.detectChanges();
    fixture.componentInstance.createCustomer();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('app-customer-quick-create form')).not.toBeNull();
  });
  it('offers to retry a failed customer search (EDGE-01)', () => {
    customers.list.and.returnValue(throwError(() => new CustomerApiError('Falla de búsqueda', 500, {})));
    const fixture = TestBed.createComponent(PatientCreateComponent); fixture.detectChanges();
    expect(fixture.componentInstance.searchError).toBe('Falla de búsqueda');
    expect(fixture.nativeElement.textContent).toContain('Reintentar búsqueda');
    customers.list.and.returnValue(of({ ...EMPTY_HISTORY, results: [customer] }));
    fixture.componentInstance.retryCustomers(); fixture.detectChanges();
    expect(fixture.componentInstance.searchError).toBe(''); expect(fixture.componentInstance.results).toEqual([customer]);
  });
});
