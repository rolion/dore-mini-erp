import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { tr } from '../../../core/i18n/translate';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { ProformaStatus, ProformaSummary, STATUSES, STATUS_CLASSES, statusLabel } from '../models/proforma';
import { ProformasApiService } from '../services/proformas-api.service';

/** Cotizaciones → Proformas: lista con filtros (plantilla Lista del sistema de diseño). */
@Component({
  selector: 'app-proforma-list',
  imports: [ReactiveFormsModule, RouterLink, MoneyPipe, DatePipe, TranslatePipe],
  templateUrl: './proforma-list.component.html',
})
export class ProformaListComponent implements OnInit {
  private api = inject(ProformasApiService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  readonly statuses = STATUSES;
  readonly statusLabel = statusLabel;
  readonly classes = STATUS_CLASSES;
  readonly filters = this.fb.group({ customer: '', from: '', to: '', status: '' });

  rows: ProformaSummary[] = [];
  count = 0;
  page = 1;
  loading = false;
  error = '';

  ngOnInit(): void {
    const query = this.route.snapshot.queryParamMap;
    this.filters.patchValue({
      customer: query.get('customer') ?? '', from: query.get('from') ?? '', to: query.get('to') ?? '',
      status: query.get('status') ?? '',
    });
    this.search(Number(query.get('page')) || 1);
  }

  get hasFilters(): boolean {
    return Object.values(this.filters.getRawValue()).some(value => value !== '');
  }

  get pages(): number {
    return Math.max(1, Math.ceil(this.count / 20));
  }

  search(page = 1): void {
    this.page = page;
    const raw = this.filters.getRawValue();
    // Los filtros viven en la URL para conservarlos al volver desde el detalle.
    void this.router.navigate([], {
      relativeTo: this.route, replaceUrl: true,
      queryParams: { ...Object.fromEntries(Object.entries(raw).filter(([, value]) => value !== '')), page: page > 1 ? page : null },
    });
    this.loading = true;
    this.error = '';
    this.api.list({ ...raw, status: raw.status as ProformaStatus | '', customer: raw.customer.trim(), page })
      .pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.loading = false))
      .subscribe({
        next: result => { this.rows = result.results; this.count = result.count; },
        error: () => this.error = tr('QUOTATIONS.PROFORMAS.ERR_LISTA'),
      });
  }

  clear(): void {
    this.filters.reset();
    this.search();
  }
}
