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

@Component({ selector: 'app-patient-create', imports: [FormsModule, NgSelectModule, CustomerQuickCreateComponent], templateUrl: './patient-create.component.html' })
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
    this.selected = customer; this.existingId = ''; this.error = '';
    this.checking = !!customer;
    if (!customer) return;
    this.api.get(customer.id).pipe(finalize(() => { if (this.selected === customer) this.checking = false; }), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => { if (this.selected === customer) this.existingId = customer.id; },
      error: (error: HttpErrorResponse) => { if (this.selected === customer && error.status !== 404) this.error = errorMessage(error); },
    });
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
      error: (error: HttpErrorResponse) => { this.error = errorMessage(error); if (error.status === 409) this.existingId = customerId; },
    });
  }
}
