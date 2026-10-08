import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { Subject, of, throwError } from 'rxjs';

import { Customer, CustomerApiError, DuplicateCustomerError, DuplicateMatch } from '../../models/customer';
import { CustomersApiService } from '../../services/customers-api.service';
import { makeCustomer } from '../../testing/customer-fixtures';
import { CustomerQuickCreateComponent } from './customer-quick-create.component';

interface DuplicateHook {
  confirmDuplicate(matches: DuplicateMatch[]): Promise<boolean>;
}

const MATCHES: DuplicateMatch[] = [{ id: 'c-9', name: 'Ana Pérez', phone: '+59176543210', active: true }];

describe('CustomerQuickCreateComponent', () => {
  let fixture: ComponentFixture<CustomerQuickCreateComponent>;
  let component: CustomerQuickCreateComponent;
  let api: jasmine.SpyObj<CustomersApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;
  let toastr: jasmine.SpyObj<ToastrService>;

  function render(): HTMLElement {
    fixture = TestBed.createComponent(CustomerQuickCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => {
    api = jasmine.createSpyObj<CustomersApiService>('CustomersApiService', ['create']);
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    TestBed.configureTestingModule({
      imports: [CustomerQuickCreateComponent],
      providers: [
        { provide: CustomersApiService, useValue: api },
        { provide: NgbActiveModal, useValue: modal },
        { provide: ToastrService, useValue: toastr },
      ],
    });
  });

  it('asks only for name and optional phone (AC-27)', () => {
    const element = render();
    expect(element.querySelector('.modal-title')?.textContent).toContain('Nuevo cliente');
    expect(element.querySelectorAll('input').length).toBe(2);
    expect((element.querySelector('button[type="submit"]') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('requires a non-blank name before saving (AC-27)', () => {
    api.create.and.returnValue(of(makeCustomer()));
    const element = render();
    const submit = element.querySelector('button[type="submit"]') as HTMLButtonElement;
    component.form.patchValue({ name: '   ' });
    fixture.detectChanges();
    expect(submit.disabled).toBeTrue();
    component.form.patchValue({ name: 'Ana' });
    fixture.detectChanges();
    expect(submit.disabled).toBeFalse();
    component.submit();
    expect(api.create).toHaveBeenCalledTimes(1);
  });

  it('creates the customer with trimmed values and closes the modal returning it (AC-27)', () => {
    const created: Customer = makeCustomer({ id: 'c-5', name: 'Luis' });
    api.create.and.returnValue(of(created));
    render();
    component.form.setValue({ name: ' Luis ', phone: ' 7654 3210 ' });
    component.submit();
    expect(api.create).toHaveBeenCalledOnceWith({ name: 'Luis', phone: '7654 3210', email: '', notes: '' }, false);
    expect(modal.close).toHaveBeenCalledOnceWith(created);
    expect(toastr.success).toHaveBeenCalledWith('Cliente creado');
  });

  it('does not submit twice while saving (AC-27)', () => {
    api.create.and.returnValue(new Subject<Customer>());
    render();
    component.form.patchValue({ name: 'Ana' });
    component.submit();
    component.submit();
    expect(api.create).toHaveBeenCalledTimes(1);
  });

  it('closes without a customer when the user dismisses it', () => {
    const element = render();
    (element.querySelector('.btn-close') as HTMLButtonElement).click();
    expect(modal.dismiss).toHaveBeenCalled();
    (element.querySelector('.modal-footer .btn-light') as HTMLButtonElement).click();
    expect(modal.dismiss).toHaveBeenCalledTimes(2);
    expect(modal.close).not.toHaveBeenCalled();
  });

  it('shows the server errors under the fields (AC-27)', () => {
    api.create.and.returnValue(
      throwError(() => new CustomerApiError('Revisa', 400, { name: ['Nombre inválido.'], phone: ['Teléfono largo.'] })),
    );
    const element = render();
    component.form.patchValue({ name: 'Ana' });
    component.submit();
    fixture.detectChanges();
    expect(element.querySelector('[data-testid="name-error"]')?.textContent).toContain('Nombre inválido.');
    expect(element.querySelector('[data-testid="phone-error"]')?.textContent).toContain('Teléfono largo.');
    expect(modal.close).not.toHaveBeenCalled();
    expect(component.saving).toBeFalse();
  });

  it('toasts errors that are not tied to a field', () => {
    api.create.and.returnValue(throwError(() => new CustomerApiError('Sin conexión', 0)));
    render();
    component.form.patchValue({ name: 'Ana' });
    component.submit();
    expect(toastr.error).toHaveBeenCalledWith('Sin conexión');
  });

  describe('duplicate phone (AC-27, REQ-CUS-006)', () => {
    it('asks for confirmation and creates anyway when the user accepts', fakeAsync(() => {
      const created = makeCustomer({ id: 'c-6' });
      api.create.and.returnValues(
        throwError(() => new DuplicateCustomerError('Ya existe', MATCHES)),
        of(created),
      );
      render();
      const confirm = spyOn(component as unknown as DuplicateHook, 'confirmDuplicate').and.resolveTo(true);
      component.form.patchValue({ name: 'Ana', phone: '76543210' });
      component.submit();
      flushMicrotasks();
      expect(confirm).toHaveBeenCalledOnceWith(MATCHES);
      expect(api.create.calls.allArgs().map((args) => args[1])).toEqual([false, true]);
      expect(modal.close).toHaveBeenCalledOnceWith(created);
    }));

    it('keeps the modal open with the data intact when the user cancels', fakeAsync(() => {
      api.create.and.returnValue(throwError(() => new DuplicateCustomerError('Ya existe', MATCHES)));
      render();
      spyOn(component as unknown as DuplicateHook, 'confirmDuplicate').and.resolveTo(false);
      component.form.patchValue({ name: 'Ana', phone: '76543210' });
      component.submit();
      flushMicrotasks();
      expect(api.create).toHaveBeenCalledTimes(1);
      expect(modal.close).not.toHaveBeenCalled();
      expect(component.form.getRawValue()).toEqual({ name: 'Ana', phone: '76543210' });
      expect(component.saving).toBeFalse();
    }));
  });
});
