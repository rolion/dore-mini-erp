import { importProvidersFrom } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { of, throwError } from 'rxjs';
import { AuthService, User } from '@core';
import { DEFAULT_ROUTE_AFTER_LOGIN, REQUIRED_FIELDS_MESSAGE, SigninComponent } from './signin.component';

describe('SigninComponent', () => {
  let fixture: ComponentFixture<SigninComponent>;
  let component: SigninComponent;
  let auth: jasmine.SpyObj<AuthService>;
  let router: Router;

  const user: User = { id: 1, username: 'ana', firstName: 'Ana', lastName: 'P', token: 't' };

  beforeEach(async () => {
    auth = jasmine.createSpyObj<AuthService>('AuthService', ['login']);
    await TestBed.configureTestingModule({
      imports: [SigninComponent],
      providers: [
        provideRouter([]),
        importProvidersFrom(FeatherModule.pick(allIcons)),
        { provide: AuthService, useValue: auth },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(SigninComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  const fill = (username: string, password: string) =>
    component.loginForm.patchValue({ username, password });
  const alertText = (): string | undefined =>
    fixture.nativeElement.querySelector('.alert-danger')?.textContent?.trim();

  it('starts empty, without prefilled credentials (AC-09)', () => {
    expect(component.loginForm.getRawValue()).toEqual({ username: '', password: '', remember: false });
  });

  it('does not call the backend with empty fields (AC-08)', () => {
    component.onSubmit();
    fixture.detectChanges();
    expect(auth.login).not.toHaveBeenCalled();
    expect(alertText()).toBe(REQUIRED_FIELDS_MESSAGE);
  });

  it('navigates to the dashboard on successful login (AC-03)', () => {
    auth.login.and.returnValue(of(user));
    fill('ana', 'secret');
    component.onSubmit();
    expect(auth.login).toHaveBeenCalledWith('ana', 'secret');
    expect(router.navigate).toHaveBeenCalledWith([DEFAULT_ROUTE_AFTER_LOGIN]);
    expect(DEFAULT_ROUTE_AFTER_LOGIN).toBe('/dashboard/main');
  });

  it('shows the error and does not navigate on invalid credentials (AC-04)', () => {
    auth.login.and.returnValue(throwError(() => new Error('Credenciales inválidas')));
    fill('ana', 'mala');
    component.onSubmit();
    fixture.detectChanges();
    expect(router.navigate).not.toHaveBeenCalled();
    expect(alertText()).toBe('Credenciales inválidas');
    expect(component.loading).toBeFalse();
  });
});
