import { Component, DestroyRef, HostListener, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { HasUnsavedChanges } from '../../../core/guard/unsaved-changes.guard';
import { ServiceApiError, ServiceInput } from '../models/service';
import { ServicesApiService } from '../services/services-api.service';

@Component({ selector: 'app-service-form', imports: [ReactiveFormsModule, RouterLink], templateUrl: './service-form.component.html' })
export class ServiceFormComponent implements OnInit, HasUnsavedChanges {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private api = inject(ServicesApiService);
  private destroyRef = inject(DestroyRef);
  readonly id = this.route.snapshot.paramMap.get('id');
  readonly form = this.fb.group({
    name: this.fb.nonNullable.control('', [Validators.required, Validators.maxLength(150), Validators.pattern(/\S/)]),
    code: this.fb.nonNullable.control('', Validators.maxLength(50)),
    description: this.fb.nonNullable.control('', Validators.maxLength(5000)),
    basePrice: this.fb.nonNullable.control('', [Validators.required, Validators.pattern(/^\d{1,10}(\.\d{1,2})?$/)]),
    durationMinutes: this.fb.control<number | null>(null, [Validators.required, Validators.min(1), Validators.max(2147483647), Validators.pattern(/^\d+$/)]),
    specialtyId: this.fb.control<string | null>({ value: null, disabled: true }),
  });
  readonly fieldLabels = { name: 'Nombre', code: 'Código', description: 'Descripción', basePrice: 'Precio base (Bs)', durationMinutes: 'Duración (minutos)' };
  readonly textFields = ['name', 'code'] as const;
  loading = false;
  saving = false;
  loadFailed = false;
  error = '';
  active = true;
  serverErrors: Partial<Record<keyof ServiceInput, string>> = {};
  get cancelLink(): string[] { return this.id ? ['/pocketbiz/catalog/services', this.id] : ['/pocketbiz/catalog/services']; }

  ngOnInit(): void {
    this.form.controls.code.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(value => {
      const upper = value.toUpperCase();
      if (upper !== value) this.form.controls.code.setValue(upper, { emitEvent: false });
    });
    if (this.id) this.load();
  }
  load(): void {
    if (!this.id || this.loading) return;
    this.loading = true; this.loadFailed = false; this.error = '';
    this.api.get(this.id).pipe(finalize(() => this.loading = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: service => { this.form.patchValue(service); this.active = service.active; this.form.markAsPristine(); },
      error: (error: ServiceApiError) => { this.error = error.message; this.loadFailed = true; },
    });
  }
  fieldError(field: keyof ServiceInput): string {
    if (this.serverErrors[field]) return this.serverErrors[field] ?? '';
    const control = this.form.controls[field];
    if (!control.touched || !control.invalid) return '';
    return field === 'basePrice' ? 'Ingresa un precio no negativo con hasta 2 decimales.'
      : field === 'durationMinutes' ? 'Ingresa minutos enteros mayores que cero.' : 'Revisa este campo y su longitud máxima.';
  }
  save(): void {
    if (this.saving || this.loading || this.loadFailed) return;
    this.form.markAllAsTouched();
    if (this.form.invalid) return;
    const raw = this.form.getRawValue();
    if (raw.durationMinutes === null) return;
    const input: ServiceInput = { ...raw, code: raw.code.trim().toUpperCase(), durationMinutes: raw.durationMinutes };
    this.saving = true; this.error = ''; this.serverErrors = {};
    const request = this.id ? this.api.update(this.id, input) : this.api.create(input);
    request.pipe(finalize(() => this.saving = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: service => { this.form.markAsPristine(); void this.router.navigate(['/pocketbiz/catalog/services', service.id], { state: { saved: true } }); },
      error: (error: ServiceApiError) => { this.error = error.message; this.serverErrors = error.fields; },
    });
  }
  hasUnsavedChanges(): boolean { return this.form.dirty; }
  @HostListener('window:beforeunload', ['$event'])
  beforeUnload(event: BeforeUnloadEvent): void { if (this.hasUnsavedChanges()) { event.preventDefault(); event.returnValue = ''; } }
}
