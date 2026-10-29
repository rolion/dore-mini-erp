import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';

import { SupplierApiError } from '../../models/supplier';
import { SuppliersApiService } from '../../services/suppliers-api.service';
import { makeSupplier } from '../../testing/supplier-fixtures';
import { SupplierFormComponent } from './supplier-form.component';

describe('SupplierFormComponent', () => {
  let fixture: ComponentFixture<SupplierFormComponent>;
  let component: SupplierFormComponent;
  let api: jasmine.SpyObj<SuppliersApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let router: Router;

  async function setup(id: string | null): Promise<void> {
    api = jasmine.createSpyObj<SuppliersApiService>('SuppliersApiService', ['get', 'create', 'update']);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    await TestBed.configureTestingModule({
      imports: [SupplierFormComponent],
      providers: [
        provideRouter([]),
        { provide: SuppliersApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap(id ? { id } : {}) } } },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(SupplierFormComponent);
    component = fixture.componentInstance;
  }

  function fillForm(values: Partial<ReturnType<typeof component.form.getRawValue>>): void {
    component.form.patchValue(values);
  }

  describe('create', () => {
    beforeEach(async () => {
      await setup(null);
      fixture.detectChanges();
    });

    it('requires only the name; the other fields are optional (AC-11)', () => {
      expect(component.form.invalid).toBeTrue();
      fillForm({ name: 'Sur' });
      expect(component.form.valid).toBeTrue();
      const button = fixture.debugElement.query(By.css('button[type="submit"]')).nativeElement as HTMLButtonElement;
      fixture.detectChanges();
      expect(button.disabled).toBeFalse();
    });

    it('rejects a blank name and an invalid email only when informed (AC-11)', () => {
      fillForm({ name: '   ' });
      expect(component.form.controls.name.hasError('required')).toBeTrue();
      fillForm({ name: 'Sur', email: 'mal' });
      expect(component.form.controls.email.hasError('pattern')).toBeTrue();
      fillForm({ email: '   ' });
      expect(component.form.controls.email.valid).toBeTrue();
      fillForm({ email: 'a@b.com' });
      expect(component.form.controls.email.valid).toBeTrue();
    });

    it('shows the email error next to its field (AC-11)', () => {
      fillForm({ name: 'Sur', email: 'mal' });
      component.form.controls.email.markAsTouched();
      fixture.detectChanges();
      expect((fixture.nativeElement as HTMLElement).textContent).toContain('Ingresa un correo válido.');
    });

    it('submits trimmed values, notifies and navigates to the detail (AC-11)', () => {
      api.create.and.returnValue(of(makeSupplier({ id: 'new' })));
      fillForm({ name: '  Sur ', taxId: ' NIT ', phone: '', email: ' a@b.com ', notes: ' n ' });

      component.onSubmit();

      expect(api.create).toHaveBeenCalledOnceWith({
        name: 'Sur', taxId: 'NIT', phone: '', email: 'a@b.com', notes: 'n',
      });
      expect(toastr.success).toHaveBeenCalledWith('Proveedor creado');
      expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases/suppliers', 'new']);
    });

    it('does not submit an invalid form (AC-11)', () => {
      component.onSubmit();
      expect(api.create).not.toHaveBeenCalled();
    });

    it('shows server errors under each field and clears them on edit (AC-11)', () => {
      api.create.and.returnValue(
        throwError(() => new SupplierApiError('Revisa los datos ingresados.', 400, {
          name: ['Nombre inválido'], taxId: ['Identificación inválida'],
        })),
      );
      fillForm({ name: 'Sur' });

      component.onSubmit();
      fixture.detectChanges();

      const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
      expect(text).toContain('Nombre inválido');
      expect(text).toContain('Identificación inválida');
      expect(toastr.error).not.toHaveBeenCalled();
      expect(component.saving).toBeFalse();

      fillForm({ name: 'Sur 2' });
      expect(component.serverErrors).toEqual({});
    });

    it('shows a toast for errors without field details (AC-11)', () => {
      api.create.and.returnValue(throwError(() => new SupplierApiError('Sin conexión', 0)));
      fillForm({ name: 'Sur' });
      component.onSubmit();
      expect(toastr.error).toHaveBeenCalledWith('Sin conexión');
    });

    it('cancel goes back to the list (AC-11)', () => {
      const cancel = fixture.debugElement.query(By.css('a.btn-light')).nativeElement as HTMLAnchorElement;
      expect(cancel.getAttribute('href')).toBe('/pocketbiz/purchases/suppliers');
    });
  });

  describe('edit', () => {
    beforeEach(async () => {
      await setup('s-1');
      api.get.and.returnValue(of(makeSupplier()));
      fixture.detectChanges();
    });

    it('loads the supplier into the form (AC-11)', () => {
      expect(component.isEdit).toBeTrue();
      expect(component.form.getRawValue()).toEqual({
        name: 'Distribuidora Sur', taxId: 'NIT-1020', phone: '76543210', email: 'ventas@sur.com', notes: 'Entrega los martes',
      });
    });

    it('updates and navigates to the detail (AC-11)', () => {
      api.update.and.returnValue(of(makeSupplier()));
      fillForm({ notes: '' });

      component.onSubmit();

      expect(api.update).toHaveBeenCalledWith('s-1', jasmine.objectContaining({ notes: '' }));
      expect(toastr.success).toHaveBeenCalledWith('Proveedor actualizado');
      expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases/suppliers', 's-1']);
    });

    it('cancel goes back to the detail (AC-11)', () => {
      fixture.detectChanges();
      const cancel = fixture.debugElement.query(By.css('a.btn-light')).nativeElement as HTMLAnchorElement;
      expect(cancel.getAttribute('href')).toBe('/pocketbiz/purchases/suppliers/s-1');
    });
  });

  it('returns to the list with a toast when the supplier does not exist (AC-11)', async () => {
    await setup('missing');
    api.get.and.returnValue(throwError(() => new SupplierApiError('Proveedor no encontrado.', 404)));
    fixture.detectChanges();
    expect(toastr.error).toHaveBeenCalledWith('Proveedor no encontrado.');
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases/suppliers']);
  });
});
