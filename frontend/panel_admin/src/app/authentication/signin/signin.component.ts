import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';
import { NonNullableFormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { FeatherModule } from 'angular-feather';
import { finalize } from 'rxjs';
import { AuthService } from '@core';

export const REQUIRED_FIELDS_MESSAGE = 'Usuario y contraseña son obligatorios.';
export const DEFAULT_ROUTE_AFTER_LOGIN = '/dashboard/main';

@Component({
    selector: 'app-signin',
    templateUrl: './signin.component.html',
    styleUrls: ['./signin.component.scss'],
    imports: [
        ReactiveFormsModule,
        FeatherModule,
        RouterLink,
    ]
})
export class SigninComponent {
  private formBuilder = inject(NonNullableFormBuilder);
  private router = inject(Router);
  private authService = inject(AuthService);
  private destroyRef = inject(DestroyRef);

  loginForm = this.formBuilder.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
    remember: [false],
  });
  submitted = false;
  loading = false;
  error = '';

  get f() {
    return this.loginForm.controls;
  }

  onSubmit() {
    this.submitted = true;
    this.error = '';

    if (this.loginForm.invalid) {
      this.error = REQUIRED_FIELDS_MESSAGE;
      return;
    }

    this.loading = true;
    this.authService
      .login(this.f.username.value, this.f.password.value)
      .pipe(
        finalize(() => (this.loading = false)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: () => this.router.navigate([DEFAULT_ROUTE_AFTER_LOGIN]),
        error: (err: Error) => (this.error = err.message),
      });
  }
}
