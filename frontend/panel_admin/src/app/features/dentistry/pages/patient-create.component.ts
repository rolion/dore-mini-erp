import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { EMPTY, Subject, catchError, debounceTime, finalize, merge, switchMap } from 'rxjs';
import { Customer, CustomerApiError } from '../../customers/models/customer';
import { CustomersApiService } from '../../customers/services/customers-api.service';
import { CustomerQuickCreateService } from '../../customers/services/customer-quick-create.service';
import { DentistryApiService, errorMessage } from '../services/dentistry-api.service';

@Component({ selector: 'app-patient-create', imports: [RouterLink, ReactiveFormsModule], templateUrl: './patient-create.component.html' })
export class PatientCreateComponent implements OnInit {
  private customers = inject(CustomersApiService);
  private quickCreate = inject(CustomerQuickCreateService);
  private api = inject(DentistryApiService);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private reload = new Subject<void>();
  search = new FormControl('', { nonNullable: true });
  results: Customer[] = [];
  selected: Customer | null = null;
  total = 0;
  error = '';
  loading = false;
  saving = false;
  opening = false;
  existingId = '';
  ngOnInit() {
    merge(this.search.valueChanges.pipe(debounceTime(300)), this.reload).pipe(
      switchMap(() => {
        this.loading = true; this.error = ''; this.results = [];
        return this.customers.list({ search: this.search.value.trim(), page: 1, pageSize: 20 }).pipe(
          catchError((error: CustomerApiError) => { this.error = error.message; return EMPTY; }),
          finalize(() => this.loading = false));
      }), takeUntilDestroyed(this.destroyRef),
    ).subscribe(page => { this.results = page.results; this.total = page.count; });
    this.retry();
  }
  retry() { this.reload.next(); }
  select(customer: Customer) {
    if (this.saving) return;
    this.selected = customer; this.existingId = ''; this.error = '';
    this.api.get(customer.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => { if (this.selected?.id === customer.id) this.existingId = customer.id; },
      error: (error: HttpErrorResponse) => { if (error.status !== 404) this.error = errorMessage(error); },
    });
  }
  async createCustomer() {
    if (this.opening || this.saving) return;
    this.opening = true;
    try { const customer = await this.quickCreate.open(); if (customer && !this.destroyRef.destroyed) this.select(customer); }
    finally { this.opening = false; }
  }
  create() {
    if (!this.selected || this.saving || this.existingId) return;
    this.saving = true; this.error = '';
    const customerId = this.selected.id;
    this.api.create(customerId).pipe(finalize(() => this.saving = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: patient => this.router.navigate(['/pocketbiz/dentistry/patients', patient.id], { queryParams: { created: 'true' } }),
      error: (error: HttpErrorResponse) => { this.error = errorMessage(error); if (error.status === 409) this.existingId = customerId; },
    });
  }
}
