import { tr } from '../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { Component, DestroyRef, HostListener, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { HasUnsavedChanges } from '../../../core/guard/unsaved-changes.guard';
import { SpecialtyOption } from '../../personnel/models/profile';
import { PersonnelApiService } from '../../personnel/services/personnel-api.service';
import { ServiceApiError, ServiceInput } from '../models/service';
import { ServicesApiService } from '../services/services-api.service';

@Component({ selector: 'app-service-form', imports: [TranslatePipe, ReactiveFormsModule, RouterLink], templateUrl: './service-form.component.html' })
export class ServiceFormComponent implements OnInit, HasUnsavedChanges {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private api = inject(ServicesApiService);
  private personnel = inject(PersonnelApiService);
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
  get fieldLabels() {
    return { name: tr('SERVICES.SERVICE_FORM.NOMBRE'), code: tr('SERVICES.SERVICE_FORM.CODIGO'), description: tr('SERVICES.SERVICE_FORM.DESCRIPCION'), basePrice: tr('SERVICES.SERVICE_FORM.PRECIO_BASE_BS_2'), durationMinutes: tr('SERVICES.SERVICE_FORM.DURACION_MINUTOS_2') };
  }
  readonly textFields = ['name', 'code'] as const;
  loading = false;
  saving = false;
  loadFailed = false;
  error = '';
  active = true;
  serverErrors: Partial<Record<keyof ServiceInput, string>> = {};
  specialties: SpecialtyOption[] = [];
  specialtiesAvailable = false;
  get cancelLink(): string[] { return this.id ? ['/pocketbiz/catalog/services', this.id] : ['/pocketbiz/catalog/services']; }

  ngOnInit(): void {
    this.personnel.specialties().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: rows => {
        const active = rows.filter(row => row.active);
        const selected = this.specialties.find(row => row.id === this.form.controls.specialtyId.value);
        this.specialties = selected && !active.some(row => row.id === selected.id)
          ? [selected, ...active] : active;
        this.specialtiesAvailable = true;
        this.form.controls.specialtyId.enable({ emitEvent: false });
      },
      error: () => { this.specialtiesAvailable = false; },
    });
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
      next: service => {
        this.form.patchValue(service);
        if (service.specialtyId && service.specialtyName &&
            !this.specialties.some(row => row.id === service.specialtyId)) {
          this.specialties = [{ id: service.specialtyId, name: service.specialtyName, active: false }, ...this.specialties];
        }
        this.active = service.active; this.form.markAsPristine();
      },
      error: (error: ServiceApiError) => { this.error = error.message; this.loadFailed = true; },
    });
  }
  fieldError(field: keyof ServiceInput): string {
    if (this.serverErrors[field]) return this.serverErrors[field] ?? '';
    const control = this.form.controls[field];
    if (!control.touched || !control.invalid) return '';
    return field === 'basePrice' ? tr('SERVICES.SERVICE_FORM.INGRESA_UN_PRECIO_NO_NEGATIVO')
      : field === 'durationMinutes' ? tr('SERVICES.SERVICE_FORM.INGRESA_MINUTOS_ENTEROS_MAYORES_QUE') : tr('SERVICES.SERVICE_FORM.REVISA_ESTE_CAMPO_Y_SU');
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
