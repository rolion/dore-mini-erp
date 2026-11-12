import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize } from 'rxjs';
import { tr } from '../../../core/i18n/translate';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import {
  ObligationSummary, PAYMENT_STATUSES, PAYMENT_TONES, PaymentStatus, statusLabel,
} from '../../../shared/models/receivable';
import { ReceivablesApiService } from '../../../shared/services/receivables-api.service';

/** Cobros: lista de obligaciones con filtros (plantilla «Lista de solo lectura con filtros»). */
@Component({
  selector: 'app-obligation-list',
  imports: [ReactiveFormsModule, RouterLink, MoneyPipe, DatePipe, TranslatePipe, StatusBadgeComponent],
  templateUrl: './obligation-list.component.html',
})
export class ObligationListComponent implements OnInit {
  private api = inject(ReceivablesApiService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  readonly statuses = PAYMENT_STATUSES;
  readonly statusLabel = statusLabel;
  readonly tones = PAYMENT_TONES;
  readonly filters = this.fb.group({ customer_id: '', date_from: '', date_to: '', status: '' });

  rows: ObligationSummary[] = [];
  count = 0;
  page = 1;
  loading = false;
  error = '';

  ngOnInit(): void {
    const query = this.route.snapshot.queryParamMap;
    this.filters.patchValue({
      customer_id: query.get('customer_id') ?? '', date_from: query.get('date_from') ?? '',
      date_to: query.get('date_to') ?? '', status: query.get('status') ?? '',
    });
    this.search(Number(query.get('page')) || 1);
  }

  get hasFilters(): boolean {
    return Object.values(this.filters.getRawValue()).some((value) => value !== '');
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
    this.api
      .list({ ...raw, status: raw.status as PaymentStatus | '', page })
      .pipe(takeUntilDestroyed(this.destroyRef), finalize(() => (this.loading = false)))
      .subscribe({
        next: (result) => { this.rows = result.results; this.count = result.count; },
        error: () => (this.error = tr('RECEIVABLES.ERR_LISTA')),
      });
  }

  clear(): void {
    this.filters.reset();
    this.search();
  }
}
