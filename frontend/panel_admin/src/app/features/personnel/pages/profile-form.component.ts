import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgSelectModule } from '@ng-select/ng-select';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, finalize, of, switchMap } from 'rxjs';
import { ProfileInput, ProfileKind, SpecialtyOption, UserOption } from '../models/profile';
import { PersonnelApiService, profileError } from '../services/personnel-api.service';

@Component({
  selector: 'app-personnel-form', templateUrl: './profile-form.component.html',
  imports: [ReactiveFormsModule, RouterLink, NgSelectModule],
})
export class ProfileFormComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private api = inject(PersonnelApiService);
  private destroyRef = inject(DestroyRef);
  readonly kind = this.route.snapshot.data['kind'] as ProfileKind;
  readonly title = this.kind === 'professionals' ? 'Profesional' : 'Especialidad';
  readonly base = `/pocketbiz/personnel/${this.kind}`;
  readonly professional = this.kind === 'professionals';
  readonly userSearch$ = new Subject<string>();
  readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [(control: AbstractControl<string>) => control.value.trim() ? null : { required: true }, Validators.maxLength(150)]],
    identification: ['', Validators.maxLength(50)], phone: ['', Validators.maxLength(30)],
    email: ['', [Validators.maxLength(254), Validators.pattern(/^(\s*|[^@\s]+@[^@\s]+\.[^@\s]+)$/)]],
    registration_number: ['', Validators.maxLength(100)],
    specialty_ids: [[] as string[]], user_id: [null as number | null],
  });
  id: string | null = null;
  loading = false;
  saving = false;
  error = '';
  lookupError = '';
  fieldErrors: Record<string, string> = {};
  specialties: SpecialtyOption[] = [];
  users: UserOption[] = [];

  ngOnInit(): void {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.fieldErrors = {});
    this.route.paramMap.pipe(switchMap(params => {
      this.id = params.get('id');
      this.loading = !!this.id;
      return this.id ? this.api.get(this.kind, this.id).pipe(finalize(() => this.loading = false)) : of(null);
    }), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: item => {
        if (!item) return;
        this.form.patchValue({ name: item.name, identification: item.identification || '', phone: item.phone || '',
          email: item.email || '', registration_number: item.registration_number || '',
          specialty_ids: item.specialty_ids || [], user_id: item.user_id ?? null });
        if (item.user_id) this.api.users('', item.user_id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: users => this.setUsers(users), error: error => this.lookupError = profileError(error),
        });
      }, error: error => this.error = profileError(error),
    });
    if (this.professional) {
      this.loadOptions();
      this.userSearch$.pipe(debounceTime(250), distinctUntilChanged(), switchMap(search => this.api.users(search || '').pipe(
        catchError(error => { this.lookupError = profileError(error); return EMPTY; }),
      )), takeUntilDestroyed(this.destroyRef)).subscribe(users => this.setUsers(users));
    }
  }
  loadOptions(): void {
    this.lookupError = '';
    this.api.specialties().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: items => this.specialties = items, error: error => this.lookupError = profileError(error),
    });
    this.api.users().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: users => this.setUsers(users), error: error => this.lookupError = profileError(error),
    });
  }
  private setUsers(users: UserOption[]): void {
    const selected = this.users.find(user => user.id === this.form.controls.user_id.value);
    this.users = selected && !users.some(user => user.id === selected.id) ? [selected, ...users] : users;
  }
  errorFor(key: keyof ProfileInput): string {
    if (this.fieldErrors[key]) return this.fieldErrors[key];
    const control = this.form.controls[key];
    return control?.invalid && (control.touched || control.dirty) ? 'Revisa este campo.' : '';
  }
  submit(): void {
    if (this.saving || this.loading) return;
    this.form.markAllAsTouched();
    if (this.form.invalid) return;
    const raw = this.form.getRawValue();
    const input: ProfileInput = { name: raw.name.trim() };
    if (this.professional) Object.assign(input, { identification: raw.identification.trim(), phone: raw.phone.trim(),
      email: raw.email.trim(), registration_number: raw.registration_number.trim(),
      specialty_ids: raw.specialty_ids, user_id: raw.user_id });
    this.saving = true;
    this.error = '';
    this.api.save(this.kind, input, this.id).pipe(finalize(() => this.saving = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: item => this.router.navigate([this.base, item.id], { state: { message: 'Datos guardados.' } }),
      error: (error: unknown) => {
        this.error = profileError(error);
        if (error instanceof HttpErrorResponse && error.status === 400 && error.error && typeof error.error === 'object') {
          for (const [key, messages] of Object.entries(error.error as Record<string, unknown>)) {
            if (Array.isArray(messages)) this.fieldErrors[key] = messages.map(String).join(' ');
          }
        }
      },
    });
  }
}
