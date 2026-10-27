import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';
import {
  AbstractControl,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { FeatherModule } from 'angular-feather';
import { finalize } from 'rxjs';
import { AuthService, RegisterError, RegisterField } from '@core';
import { APP_PATHS } from '../../core/routing/app-paths';

export const DEFAULT_ROUTE_AFTER_SIGNUP = APP_PATHS.dashboard;
export const INVALID_FORM_MESSAGE = 'Revisa los campos marcados.';
export const NAME_MAX_LENGTH = 150;

const REQUIRED_MESSAGES: Record<RegisterField, string> = {
  companyName: 'El nombre de la empresa es obligatorio.',
  firstName: 'El nombre es obligatorio.',
  lastName: 'El apellido es obligatorio.',
  username: 'El usuario es obligatorio.',
  email: 'El correo es obligatorio.',
  password: 'La contraseña es obligatoria.',
};

/** Rechaza textos vacíos o solo con espacios (el backend también recorta). */
function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

function passwordsMatch(group: AbstractControl): ValidationErrors | null {
  const password = group.get('password')?.value as string;
  const confirm = group.get('confirmPassword')?.value as string;
  return password === confirm ? null : { passwordMismatch: true };
}

@Component({
  selector: 'app-signup',
  templateUrl: './signup.component.html',
  styleUrls: ['./signup.component.sass'],
  imports: [ReactiveFormsModule, FeatherModule, RouterLink],
})
export class SignupComponent {
  private formBuilder = inject(NonNullableFormBuilder);
  private router = inject(Router);
  private authService = inject(AuthService);
  private destroyRef = inject(DestroyRef);

  readonly nameMaxLength = NAME_MAX_LENGTH;

  registerForm = this.formBuilder.group(
    {
      companyName: ['', [Validators.required, notBlank, Validators.maxLength(NAME_MAX_LENGTH)]],
      firstName: ['', [Validators.required, notBlank, Validators.maxLength(NAME_MAX_LENGTH)]],
      lastName: ['', [Validators.required, notBlank, Validators.maxLength(NAME_MAX_LENGTH)]],
      username: ['', [Validators.required, notBlank, Validators.maxLength(NAME_MAX_LENGTH)]],
      email: ['', [Validators.required, Validators.email, Validators.maxLength(254)]],
      password: ['', [Validators.required]],
      confirmPassword: ['', [Validators.required]],
    },
    { validators: passwordsMatch }
  );
  submitted = false;
  loading = false;
  error = '';
  serverErrors: Partial<Record<RegisterField, string>> = {};

  constructor() {
    this.registerForm.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => (this.serverErrors = {}));
  }

  get f() {
    return this.registerForm.controls;
  }

  /** Mensaje bajo un campo: el del servidor, o el de validación local una vez tocado o enviado. */
  fieldError(field: RegisterField | 'confirmPassword'): string {
    if (field !== 'confirmPassword' && this.serverErrors[field]) {
      return this.serverErrors[field] as string;
    }
    const control = this.f[field];
    const shown = this.submitted || control.touched;
    if (!shown) {
      return '';
    }
    if (field === 'confirmPassword') {
      if (control.hasError('required')) {
        return 'Confirma la contraseña.';
      }
      return this.registerForm.hasError('passwordMismatch') ? 'Las contraseñas no coinciden.' : '';
    }
    if (control.hasError('required')) {
      return REQUIRED_MESSAGES[field];
    }
    if (control.hasError('email')) {
      return 'Ingresa un correo válido.';
    }
    if (control.hasError('maxlength')) {
      return `No puede superar ${field === 'email' ? 254 : NAME_MAX_LENGTH} caracteres.`;
    }
    return '';
  }

  onSubmit() {
    this.submitted = true;
    this.error = '';
    this.serverErrors = {};

    if (this.registerForm.invalid) {
      this.registerForm.markAllAsTouched();
      this.error = INVALID_FORM_MESSAGE;
      return;
    }

    const { companyName, firstName, lastName, username, email, password } = this.registerForm.getRawValue();
    this.loading = true;
    this.authService
      .register({
        companyName: companyName.trim(),
        firstName: firstName.trim(),
        lastName: lastName.trim(),
        username: username.trim(),
        email: email.trim(),
        password,
      })
      .pipe(
        finalize(() => (this.loading = false)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: () => this.router.navigate([DEFAULT_ROUTE_AFTER_SIGNUP]),
        error: (err: Error) => {
          if (err instanceof RegisterError && Object.keys(err.fieldErrors).length) {
            this.serverErrors = err.fieldErrors;
            this.error = '';
            return;
          }
          this.error = err.message;
        },
      });
  }
}
