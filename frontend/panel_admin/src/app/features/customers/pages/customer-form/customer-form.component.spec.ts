import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { ToastrService } from 'ngx-toastr';
import { Subject, of, throwError } from 'rxjs';

import { CustomerApiError, DuplicateCustomerError, DuplicateMatch } from '../../models/customer';
import { CustomersApiService } from '../../services/customers-api.service';
import { makeCustomer } from '../../testing/customer-fixtures';
import { CustomerFormComponent, duplicateMatchesHtml, escapeHtml } from './customer-form.component';

interface DuplicateHook {
  confirmDuplicate(matches: DuplicateMatch[]): Promise<boolean>;
}

const MATCHES: DuplicateMatch[] = [{ id: 'x', name: 'Otra Ana', phone: '+59176543210', active: true }];

describe('CustomerFormComponent', () => {
  let api: jasmine.SpyObj<CustomersApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let navigate: jasmine.Spy;

  beforeEach(() => {
    api = jasmine.createSpyObj<CustomersApiService>('CustomersApiService', ['get', 'create', 'update']);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'customers/new', component: CustomerFormComponent },
          { path: 'customers/:id/edit', component: CustomerFormComponent },
        ]),
        { provide: CustomersApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
      ],
    });
    navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
  });

  async function open(url: string) {
    const harness = await RouterTestingHarness.create();
    const component = await harness.navigateByUrl(url, CustomerFormComponent);
    harness.detectChanges();
    return { harness, component, el: harness.routeNativeElement as HTMLElement };
  }

  function submitButton(el: HTMLElement): HTMLButtonElement {
    return el.querySelector('button[type="submit"]') as HTMLButtonElement;
  }

  const flush = () => new Promise<void>((resolve) => setTimeout(resolve));

  describe('create mode', () => {
    it('starts empty, without a state field, with Guardar disabled (AC-11)', async () => {
      const { component, el } = await open('/customers/new');

      expect(component.isEdit).toBeFalse();
      expect(component.form.getRawValue()).toEqual({ name: '', phone: '', email: '', notes: '' });
      expect(submitButton(el).disabled).toBeTrue();
      expect(el.textContent).toContain('Nuevo cliente');
      expect(el.querySelector('input[type="checkbox"], #customer-active')).toBeNull();
      expect(api.get).not.toHaveBeenCalled();
    });

    it('is valid with only a name; phone and email are optional (AC-01, AC-11)', async () => {
      const { component, harness, el } = await open('/customers/new');
      component.form.patchValue({ name: 'Ana' });
      harness.detectChanges();
      expect(component.form.valid).toBeTrue();
      expect(submitButton(el).disabled).toBeFalse();
    });

    it('validates name, email format and lengths on the client (AC-11)', async () => {
      const { component } = await open('/customers/new');
      const { controls } = component.form;

      controls.name.setValue('   ');
      expect(controls.name.hasError('required')).toBeTrue();
      controls.name.setValue('a'.repeat(151));
      expect(controls.name.hasError('maxlength')).toBeTrue();
      controls.name.setValue('Ana');
      expect(controls.name.valid).toBeTrue();

      controls.email.setValue('sin-arroba');
      expect(controls.email.invalid).toBeTrue();
      controls.email.setValue('a@x.com');
      expect(controls.email.valid).toBeTrue();
      controls.email.setValue('');
      expect(controls.email.valid).toBeTrue();

      controls.phone.setValue('1'.repeat(31));
      expect(controls.phone.hasError('maxlength')).toBeTrue();
      controls.notes.setValue('n'.repeat(2001));
      expect(controls.notes.hasError('maxlength')).toBeTrue();
    });

    it('creates a customer with trimmed values and goes to its profile (AC-11)', async () => {
      api.create.and.returnValue(of(makeCustomer({ id: 'new-1' })));
      const { component } = await open('/customers/new');
      component.form.setValue({ name: '  Ana  ', phone: ' 7654 3210 ', email: ' a@x.com ', notes: ' vip ' });

      component.onSubmit();

      expect(api.create).toHaveBeenCalledOnceWith(
        { name: 'Ana', phone: '7654 3210', email: 'a@x.com', notes: 'vip' },
        false,
      );
      expect(toastr.success).toHaveBeenCalledWith('Cliente creado');
      expect(navigate).toHaveBeenCalledWith(['/customers', 'new-1']);
    });

    it('does not submit an invalid form or submit twice while saving (AC-11)', async () => {
      const pending = new Subject<ReturnType<typeof makeCustomer>>();
      api.create.and.returnValue(pending);
      const { component } = await open('/customers/new');

      component.onSubmit();
      expect(api.create).not.toHaveBeenCalled();

      component.form.patchValue({ name: 'Ana' });
      component.onSubmit();
      component.onSubmit();
      expect(api.create).toHaveBeenCalledTimes(1);
      expect(component.saving).toBeTrue();
    });

    it('shows server validation errors under each field and clears them on edit (AC-11)', async () => {
      api.create.and.returnValue(
        throwError(() => new CustomerApiError('Revisa', 400, { email: ['Ingresa un correo válido.'], notes: ['Muy largas'] })),
      );
      const { component, harness, el } = await open('/customers/new');
      component.form.patchValue({ name: 'Ana' });

      component.onSubmit();
      harness.detectChanges();

      expect(el.textContent).toContain('Ingresa un correo válido.');
      expect(el.textContent).toContain('Muy largas');
      expect(component.saving).toBeFalse();
      expect(toastr.error).not.toHaveBeenCalled();

      component.form.patchValue({ notes: 'ok' });
      harness.detectChanges();
      expect(el.textContent).not.toContain('Muy largas');
    });

    it('shows a toast for errors without field details (AC-11)', async () => {
      api.create.and.returnValue(throwError(() => new CustomerApiError('Sin conexión', 0)));
      const { component } = await open('/customers/new');
      component.form.patchValue({ name: 'Ana' });

      component.onSubmit();

      expect(toastr.error).toHaveBeenCalledWith('Sin conexión');
    });

    it('cancel goes back to the list (AC-11)', async () => {
      const { el } = await open('/customers/new');
      const cancel = Array.from(el.querySelectorAll('a')).find((a) => a.textContent?.trim() === 'Cancelar');
      expect(cancel?.getAttribute('href')).toBe('/customers');
    });
  });

  describe('duplicate phone (AC-12)', () => {
    async function submitWithDuplicate() {
      api.create.and.returnValues(
        throwError(() => new DuplicateCustomerError('Ya existe', MATCHES)),
        of(makeCustomer({ id: 'new-2' })),
      );
      const opened = await open('/customers/new');
      opened.component.form.patchValue({ name: 'Ana', phone: '76543210' });
      return opened;
    }

    it('asks for confirmation with the matches and creates anyway when confirmed', async () => {
      const { component } = await submitWithDuplicate();
      const confirm = spyOn(component as unknown as DuplicateHook, 'confirmDuplicate').and.resolveTo(true);

      component.onSubmit();
      await flush();

      expect(confirm).toHaveBeenCalledOnceWith(MATCHES);
      expect(api.create.calls.allArgs()).toEqual([
        [{ name: 'Ana', phone: '76543210', email: '', notes: '' }, false],
        [{ name: 'Ana', phone: '76543210', email: '', notes: '' }, true],
      ]);
      expect(navigate).toHaveBeenCalledWith(['/customers', 'new-2']);
      expect(toastr.success).toHaveBeenCalledWith('Cliente creado');
    });

    it('does not create and keeps the form data when cancelled', async () => {
      const { component } = await submitWithDuplicate();
      spyOn(component as unknown as DuplicateHook, 'confirmDuplicate').and.resolveTo(false);

      component.onSubmit();
      await flush();

      expect(api.create).toHaveBeenCalledTimes(1);
      expect(navigate).not.toHaveBeenCalled();
      expect(component.saving).toBeFalse();
      expect(component.form.getRawValue().name).toBe('Ana');
      expect(component.form.getRawValue().phone).toBe('76543210');
    });

    it('escapes customer names and encodes ids in the dialog html', () => {
      const html = duplicateMatchesHtml([
        { id: 'a/b', name: '<img src=x onerror=alert(1)>', phone: '+59176543210', active: false },
      ]);

      expect(html).not.toContain('<img');
      expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;');
      expect(html).toContain('href="/customers/a%2Fb"');
      expect(html).toContain('target="_blank"');
      expect(html).toContain('rel="noopener"');
      expect(html).toContain('(inactivo)');
      expect(escapeHtml(`&"'<>`)).toBe('&amp;&quot;&#39;&lt;&gt;');
    });
  });

  describe('edit mode', () => {
    it('loads the customer, fills the form and updates only through update (AC-11)', async () => {
      api.get.and.returnValue(of(makeCustomer()));
      api.update.and.returnValue(of(makeCustomer({ name: 'Ana María' })));
      const { component, el } = await open('/customers/c-1/edit');

      expect(api.get).toHaveBeenCalledOnceWith('c-1');
      expect(component.isEdit).toBeTrue();
      expect(component.form.getRawValue()).toEqual({
        name: 'Ana Pérez', phone: '+59176543210', email: 'ana@example.com', notes: 'Cliente frecuente',
      });
      expect(el.textContent).toContain('Editar cliente');

      component.form.patchValue({ name: 'Ana María' });
      component.onSubmit();

      expect(api.update).toHaveBeenCalledOnceWith('c-1', {
        name: 'Ana María', phone: '+59176543210', email: 'ana@example.com', notes: 'Cliente frecuente',
      });
      expect(api.create).not.toHaveBeenCalled();
      expect(toastr.success).toHaveBeenCalledWith('Cliente actualizado');
      expect(navigate).toHaveBeenCalledWith(['/customers', 'c-1']);
    });

    it('cancel goes back to the profile (AC-11)', async () => {
      api.get.and.returnValue(of(makeCustomer()));
      const { el } = await open('/customers/c-1/edit');
      const cancel = Array.from(el.querySelectorAll('a')).find((a) => a.textContent?.trim() === 'Cancelar');
      expect(cancel?.getAttribute('href')).toBe('/customers/c-1');
    });

    it('warns and goes back to the list when the customer does not exist (AC-11)', async () => {
      api.get.and.returnValue(throwError(() => new CustomerApiError('Cliente no encontrado.', 404)));
      await open('/customers/nope/edit');
      expect(toastr.error).toHaveBeenCalledWith('Cliente no encontrado.');
      expect(navigate).toHaveBeenCalledWith(['/customers']);
    });
  });
});
