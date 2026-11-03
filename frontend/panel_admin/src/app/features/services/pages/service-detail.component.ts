import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { ServiceToggleComponent } from '../components/service-toggle.component';
import { CatalogService, ServiceApiError } from '../models/service';
import { ServicesApiService } from '../services/services-api.service';

@Component({ selector: 'app-service-detail', imports: [RouterLink, DatePipe, MoneyPipe, ServiceToggleComponent],
  templateUrl: './service-detail.component.html' })
export class ServiceDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private api = inject(ServicesApiService);
  private destroyRef = inject(DestroyRef);
  service: CatalogService | null = null;
  loading = false;
  error = '';
  saved = window.history.state?.saved === true;
  ngOnInit(): void { this.load(); }
  load(): void {
    if (this.loading) return;
    this.loading = true; this.error = '';
    this.api.get(this.route.snapshot.paramMap.get('id') ?? '').pipe(
      finalize(() => this.loading = false), takeUntilDestroyed(this.destroyRef),
    ).subscribe({ next: service => this.service = service, error: (error: ServiceApiError) => this.error = error.message });
  }
}
