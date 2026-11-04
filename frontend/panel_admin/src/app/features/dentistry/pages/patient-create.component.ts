import { TranslatePipe } from '@ngx-translate/core';
import { tr } from '../../../core/i18n/translate';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { NgSelectModule } from '@ng-select/ng-select';
import { Router } from '@angular/router';
import { EMPTY, Subject, catchError, debounceTime, finalize, startWith, switchMap, merge } from 'rxjs';
import { Customer, CustomerApiError } from '../../customers/models/customer';
import { CustomersApiService } from '../../customers/services/customers-api.service';
import { CustomerQuickCreateComponent } from '../../customers/components/customer-quick-create/customer-quick-create.component';
import { DentistryApiService, errorMessage } from '../services/dentistry-api.service';

@Component({ selector: 'app-patient-create', imports: [TranslatePipe, FormsModule, NgSelectModule, CustomerQuickCreateComponent], templateUrl: './patient-create.component.html' })
export class PatientCreateComponent implements OnInit {
  private customers = inject(CustomersApiService);
  private modal = inject(NgbActiveModal);
  private api = inject(DentistryApiService);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  readonly customerSearch = new Subject<string>();
  private readonly retrySearch = new Subject<string>();
  private lastSearch = '';
  searchError = '';
  backFilters: Record<string, string | number> = {};
  checking = false;
  results: Customer[] = [];
  selected: Customer | null = null;
  total = 0;
  error = '';
  loading = false;
  saving = false;
  opening = false;
  existingId = '';
  /** Cliente creado en este modal: si falla la ficha, se reintenta solo la ficha. */
  private fresh: Customer | null = null;
  profileFailed = false;
  ngOnInit() {
    merge(this.customerSearch.pipe(debounceTime(300)), this.retrySearch).pipe(startWith(''),
      switchMap(search => {
        this.lastSearch = search;
        this.loading = true;
        this.searchError = '';
        this.results = [];
        this.total = 0;
        return this.customers.list({ search: search.trim(), page: 1, pageSize: 20 }).pipe(
          catchError((error: CustomerApiError) => { this.searchError = error.message; return EMPTY; }),
          finalize(() => this.loading = false));
      }), takeUntilDestroyed(this.destroyRef),
    ).subscribe(page => { this.results = page.results; this.total = page.count; });
  }
  retryCustomers() {
    this.retrySearch.next(this.lastSearch);
  }
  select(customer: Customer | null) {
    if (this.saving) return;
    this.selected = customer; this.existingId = ''; this.error = ''; this.fresh = null; this.profileFailed = false;
    this.checking = !!customer;
    if (!customer) return;
    this.api.get(customer.id).pipe(finalize(() => { if (this.selected === customer) this.checking = false; }), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => { if (this.selected === customer) this.existingId = customer.id; },
      error: (error: HttpErrorResponse) => { if (this.selected === customer && error.status !== 404) this.error = errorMessage(error); },
    });
  }
  get disabledReason(): string {
    if (this.existingId || this.saving) return '';
    if (this.checking) return tr('DENTISTRY.PATIENT_CREATE.COMPROBANDO_SI_ES_PACIENTE');
    return this.selected ? '' : tr('DENTISTRY.PATIENT_CREATE.ELIGE_O_REGISTRA');
  }
  /** Persona nueva: el cliente ya existe, así que se crea la ficha sin pedir otro clic. */
  customerCreated(customer: Customer) {
    this.opening = false;
    this.selected = customer; this.existingId = ''; this.error = ''; this.profileFailed = false;
    this.fresh = customer;
    this.create();
  }
  createCustomer() {
    if (!this.saving) this.opening = true;
  }
  close() {
    if (!this.saving) this.modal.dismiss();
  }
  openRecord(id: string, created = false) {
    this.modal.close();
    void this.router.navigate(['/pocketbiz/dentistry/patients', id], {
      queryParams: { ...this.backFilters, ...(created ? { created: 'true' } : {}) },
    });
  }
  create() {
    if (!this.selected || this.saving || this.checking || this.existingId) return;
    this.saving = true; this.error = '';
    const customerId = this.selected.id;
    this.api.create(customerId).pipe(finalize(() => this.saving = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: patient => this.openRecord(patient.id, true),
      error: (error: HttpErrorResponse) => {
        if (error.status === 409) { this.existingId = customerId; this.error = ''; return; }
        if (this.fresh?.id === customerId) {
          this.profileFailed = true;
          this.error = tr('DENTISTRY.PATIENT_CREATE.CLIENTE_SIN_FICHA', { name: this.fresh.name });
        } else this.error = errorMessage(error);
      },
    });
  }
}
