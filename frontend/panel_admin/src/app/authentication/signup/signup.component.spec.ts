import { importProvidersFrom } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { of, throwError } from 'rxjs';
import { AuthService, RegisterError, User } from '@core';
import { DEFAULT_ROUTE_AFTER_SIGNUP, INVALID_FORM_MESSAGE, SignupComponent } from './signup.component';

describe('SignupComponent', () => {
  let fixture: ComponentFixture<SignupComponent>;
  let component: SignupComponent;
  let auth: jasmine.SpyObj<AuthService>;
  let router: Router;

  const user: User = { id: 1, username: 'maria', firstName: 'María', lastName: 'Q', token: 't' };
  const validValues = {
    companyName: '  Cuñapés SRL ',
    firstName: 'María',
    lastName: 'Quispe',
    username: 'maria',
    email: 'maria@example.com',
    password: 'Cl4ve-segura-2026',
    confirmPassword: 'Cl4ve-segura-2026',
  };

  beforeEach(async () => {
    auth = jasmine.createSpyObj<AuthService>('AuthService', ['register']);
    await TestBed.configureTestingModule({
      imports: [SignupComponent],
      providers: [
        provideRouter([]),
        importProvidersFrom(FeatherModule.pick(allIcons)),
        { provide: AuthService, useValue: auth },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(SignupComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  const el = (): HTMLElement => fixture.nativeElement;
  const text = (selector: string): string | undefined => el().querySelector(selector)?.textContent?.trim();
  const submit = () => {
    component.onSubmit();
    fixture.detectChanges();
  };

  it('uses the same single card and logo as the login, without side image, social or terms (AC-14)', () => {
    expect(el().querySelector('.login-card.login-card--single')).toBeTruthy();
    expect(el().querySelector('.register-card-img')).toBeNull();
    const logo = el().querySelector<HTMLImageElement>('.brand-wrapper img.logo');
    expect(logo?.getAttribute('src')).toBe('assets/images/main-logo.png');
    expect(logo?.getAttribute('alt')).toBe('PocketBiz');
    expect(el().querySelector('.social-icon')).toBeNull();
    expect(el().querySelector('input[type="checkbox"]')).toBeNull();
  });

  it('shows the company field first and required (AC-14)', () => {
    const inputs = Array.from(el().querySelectorAll('input')).map((i) => i.getAttribute('formcontrolname'));
    expect(inputs).toEqual(['companyName', 'firstName', 'lastName', 'username', 'email', 'password', 'confirmPassword']);
    expect(el().querySelector('label[for="signup-company"]')?.textContent).toContain('Nombre de la empresa');
  });

  it('does not call the backend with an empty form and marks the fields (AC-14)', () => {
    submit();
    expect(auth.register).not.toHaveBeenCalled();
    expect(text('.alert-danger')).toBe(INVALID_FORM_MESSAGE);
    expect(component.fieldError('companyName')).toBe('El nombre de la empresa es obligatorio.');
    expect(el().querySelectorAll('.text-danger.form-text').length).toBeGreaterThanOrEqual(6);
  });

  it('rejects a blank company name made of spaces (AC-14, EDGE-06)', () => {
    component.registerForm.patchValue({ ...validValues, companyName: '   ' });
    submit();
    expect(auth.register).not.toHaveBeenCalled();
    expect(component.fieldError('companyName')).toBe('El nombre de la empresa es obligatorio.');
  });

  it('validates the email format and that both passwords match (AC-14)', () => {
    component.registerForm.patchValue({ ...validValues, email: 'no-es-correo', confirmPassword: 'otra' });
    submit();
    expect(auth.register).not.toHaveBeenCalled();
    expect(component.fieldError('email')).toBe('Ingresa un correo válido.');
    expect(component.fieldError('confirmPassword')).toBe('Las contraseñas no coinciden.');
  });

  it('registers with trimmed values and goes to the dashboard (AC-14, UI-03)', () => {
    auth.register.and.returnValue(of(user));
    component.registerForm.patchValue(validValues);
    submit();

    expect(auth.register).toHaveBeenCalledOnceWith({
      companyName: 'Cuñapés SRL',
      firstName: 'María',
      lastName: 'Quispe',
      username: 'maria',
      email: 'maria@example.com',
      password: 'Cl4ve-segura-2026',
    });
    expect(router.navigate).toHaveBeenCalledWith([DEFAULT_ROUTE_AFTER_SIGNUP]);
    expect(component.loading).toBeFalse();
  });

  it('shows server field errors under each control and clears them on edit (AC-02, AC-14)', () => {
    auth.register.and.returnValue(
      throwError(() => new RegisterError('Revisa', { companyName: 'Ya existe una empresa con ese nombre.' }))
    );
    component.registerForm.patchValue(validValues);
    submit();

    expect(router.navigate).not.toHaveBeenCalled();
    expect(component.fieldError('companyName')).toBe('Ya existe una empresa con ese nombre.');
    expect(el().textContent).toContain('Ya existe una empresa con ese nombre.');
    expect(el().querySelector('.alert-danger')).toBeNull();

    component.registerForm.patchValue({ companyName: 'Otra SRL' });
    fixture.detectChanges();
    expect(component.fieldError('companyName')).toBe('');
  });

  it('shows general errors (disabled, throttle, network) in the alert (AC-11, AC-14)', () => {
    auth.register.and.returnValue(throwError(() => new RegisterError('Demasiados intentos.')));
    component.registerForm.patchValue(validValues);
    submit();

    expect(text('.alert-danger')).toBe('Demasiados intentos.');
    expect(router.navigate).not.toHaveBeenCalled();
    expect(component.loading).toBeFalse();
  });

  it('links back to the login', () => {
    const link = el().querySelector<HTMLAnchorElement>('a[href="/authentication/signin"]');
    expect(link?.textContent).toContain('Inicia sesión');
  });
});
