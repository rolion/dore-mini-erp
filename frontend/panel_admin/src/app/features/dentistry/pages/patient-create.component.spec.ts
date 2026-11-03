import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';
import { CustomersApiService } from '../../customers/services/customers-api.service';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { Customer } from '../../customers/models/customer';
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
    await TestBed.configureTestingModule({ imports: [PatientCreateComponent], providers: [provideRouter([]),
      { provide: DentistryApiService, useValue: api }, { provide: CustomersApiService, useValue: customers },
      { provide: NgbActiveModal, useValue: { close: () => undefined, dismiss: () => undefined } },
      { provide: ToastrService, useValue: {} },
    ] }).compileComponents();
  });
  it('opens an existing profile without allowing duplicate creation', () => {
    api.get.and.returnValue(of(makePatient()));
    const fixture = TestBed.createComponent(PatientCreateComponent); fixture.detectChanges();
    fixture.componentInstance.select(customer); fixture.componentInstance.create(); fixture.detectChanges();
    expect(api.create).not.toHaveBeenCalled(); expect(fixture.nativeElement.textContent).toContain('Abrir ficha existente');
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
});
