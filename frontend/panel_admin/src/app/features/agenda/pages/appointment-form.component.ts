import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { debounceTime, finalize } from 'rxjs';
import { Customer } from '../../customers/models/customer';
import { CustomersApiService } from '../../customers/services/customers-api.service';
import { Profile } from '../../personnel/models/profile';
import { PersonnelApiService } from '../../personnel/services/personnel-api.service';
import { CatalogService } from '../../services/models/service';
import { ServicesApiService } from '../../services/services/services-api.service';
import { AppointmentFailure, NOTES_MAX_LENGTH, Slot } from '../models/appointment';
import { AppointmentsApiService, toServerDateTime } from '../services/appointments-api.service';
import { fetchAll } from '../services/fetch-all';

/** Alta de cita (plantilla Formulario del sistema de diseño). Ante un conflicto conserva lo escrito y refresca franjas. */
@Component({
  selector: 'app-appointment-form',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './appointment-form.component.html',
})
export class AppointmentFormComponent implements OnInit {
  private api = inject(AppointmentsApiService);
  private customersApi = inject(CustomersApiService);
  private servicesApi = inject(ServicesApiService);
  private personnel = inject(PersonnelApiService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;

  readonly notesMax = NOTES_MAX_LENGTH;
  readonly customerSearch = this.fb.control('');
  readonly form = this.fb.group({
    customer_id: ['', Validators.required],
    professional_id: ['', Validators.required],
    service_id: ['', Validators.required],
    starts: ['', Validators.required],
    duration_minutes: [30, [Validators.required, Validators.min(1), Validators.max(1440)]],
    notes: ['', Validators.maxLength(NOTES_MAX_LENGTH)],
  });

  customers: Customer[] = [];
  customersTotal = 0;
  services: CatalogService[] = [];
  people: Profile[] = [];
  slots: Slot[] = [];
  saving = false;
  loadingOptions = true;
  error = '';
  conflict = false;
  fields: Record<string, string> = {};

  ngOnInit(): void {
    const query = this.route.snapshot.queryParamMap;
    this.form.patchValue({ professional_id: query.get('professional') ?? '', starts: query.get('starts') ?? '' });
    let pending = 3;
    const done = () => { if (--pending === 0) this.loadingOptions = false; };
    const fail = () => { this.error = 'No se pudieron cargar los datos del formulario.'; done(); };
    fetchAll(page => this.personnel.list('professionals', { page, page_size: 100 })).pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: people => { this.people = people.filter(person => person.active); done(); }, error: fail });
    fetchAll(page => this.servicesApi.list({ active: true, pageSize: 100, page })).pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: services => { this.services = services; done(); }, error: fail });
    this.searchCustomers('', done);
    this.customerSearch.valueChanges.pipe(debounceTime(300), takeUntilDestroyed(this.destroyRef))
      .subscribe(term => this.searchCustomers(term));
    this.form.controls.service_id.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(id => {
      const service = this.services.find(item => item.id === id);
      if (service) this.form.controls.duration_minutes.setValue(service.durationMinutes);
    });
  }

  private searchCustomers(term: string, done?: () => void): void {
    this.customersApi.list({ active: true, search: term.trim(), pageSize: 50 }).pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: page => { this.customers = page.results; this.customersTotal = page.count; done?.(); },
        error: () => { this.error = 'No se pudieron cargar los clientes.'; done?.(); },
      });
  }

  get endsLabel(): string {
    const { starts, duration_minutes } = this.form.getRawValue();
    if (!starts || !duration_minutes || duration_minutes < 1) return '—';
    const date = new Date(`${starts}:00Z`);
    date.setUTCMinutes(date.getUTCMinutes() + duration_minutes);
    const iso = date.toISOString();
    return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)} ${iso.slice(11, 16)}`;
  }

  time(value: string): string {
    return value.slice(11, 16);
  }

  submit(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid || this.saving) return;
    const value = this.form.getRawValue();
    this.saving = true;
    this.error = '';
    this.conflict = false;
    this.fields = {};
    this.api.create({ ...value, starts: toServerDateTime(value.starts) }).pipe(
      takeUntilDestroyed(this.destroyRef), finalize(() => this.saving = false),
    ).subscribe({
      next: appointment => void this.router.navigate(['/pocketbiz/agenda/citas', appointment.id]),
      error: (failure: AppointmentFailure) => this.fail(failure),
    });
  }

  private fail(failure: AppointmentFailure): void {
    this.error = failure.message;
    this.fields = failure.fields;
    this.conflict = failure.conflict;
    if (failure.conflict) this.refreshSlots();
  }

  /** Tras un conflicto se vuelve a consultar la disponibilidad del día sin tocar los datos escritos. */
  refreshSlots(): void {
    const { professional_id, starts, duration_minutes } = this.form.getRawValue();
    if (!professional_id || !starts) return;
    const day = starts.slice(0, 10);
    this.api.freeSlots(professional_id, day, day, duration_minutes || undefined).pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: result => this.slots = result.slots, error: () => this.slots = [] });
  }

  useSlot(slot: Slot): void {
    this.form.controls.starts.setValue(slot.starts.slice(0, 16));
    this.conflict = false;
    this.error = '';
  }
}
