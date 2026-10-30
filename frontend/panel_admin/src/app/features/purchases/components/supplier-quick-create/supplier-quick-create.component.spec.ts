import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';

import { SupplierApiError } from '../../models/supplier';
import { SuppliersApiService } from '../../services/suppliers-api.service';
import { makeSupplier } from '../../testing/supplier-fixtures';
import { SupplierQuickCreateComponent } from './supplier-quick-create.component';

describe('SupplierQuickCreateComponent', () => {
  let fixture: ComponentFixture<SupplierQuickCreateComponent>;
  let component: SupplierQuickCreateComponent;
  let api: jasmine.SpyObj<SuppliersApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;
  let toastr: jasmine.SpyObj<ToastrService>;

  beforeEach(() => {
    api = jasmine.createSpyObj<SuppliersApiService>('SuppliersApiService', ['create']);
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    TestBed.configureTestingModule({
      imports: [SupplierQuickCreateComponent],
      providers: [
        { provide: SuppliersApiService, useValue: api },
        { provide: NgbActiveModal, useValue: modal },
        { provide: ToastrService, useValue: toastr },
      ],
    });
    fixture = TestBed.createComponent(SupplierQuickCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('requires the name and disables saving without it (AC-14)', () => {
    expect(component.form.invalid).toBeTrue();
    component.form.patchValue({ name: '   ' });
    expect(component.form.controls.name.hasError('required')).toBeTrue();
    component.submit();
    expect(api.create).not.toHaveBeenCalled();
  });

  it('validates the email only when informed (AC-14)', () => {
    component.form.patchValue({ name: 'Sur', email: 'mal' });
    expect(component.form.controls.email.hasError('pattern')).toBeTrue();
    component.form.patchValue({ email: '' });
    expect(component.form.valid).toBeTrue();
  });

  it('creates the supplier, notifies and closes the dialog returning it (AC-14)', () => {
    const created = makeSupplier({ id: 's-9', name: 'Nuevo' });
    api.create.and.returnValue(of(created));
    component.form.patchValue({ name: ' Nuevo ', taxId: ' NIT-1 ', phone: '', email: '' });
    component.submit();
    expect(api.create).toHaveBeenCalledWith({ name: 'Nuevo', taxId: 'NIT-1', phone: '', email: '', notes: '' });
    expect(toastr.success).toHaveBeenCalledWith('Proveedor creado');
    expect(modal.close).toHaveBeenCalledWith(created);
  });

  it('shows server errors under their field and keeps the dialog open (AC-14)', () => {
    api.create.and.returnValue(throwError(() => new SupplierApiError('Revisa los datos ingresados.', 400, { name: ['El nombre es obligatorio.'] })));
    component.form.patchValue({ name: 'Sur' });
    component.submit();
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('El nombre es obligatorio.');
    expect(modal.close).not.toHaveBeenCalled();
    expect(component.saving).toBeFalse();
  });

  it('toasts an error that has no field (AC-14)', () => {
    api.create.and.returnValue(throwError(() => new SupplierApiError('Ocurrió un error inesperado. Inténtalo de nuevo.', 500)));
    component.form.patchValue({ name: 'Sur' });
    component.submit();
    expect(toastr.error).toHaveBeenCalledWith('Ocurrió un error inesperado. Inténtalo de nuevo.');
  });
});
