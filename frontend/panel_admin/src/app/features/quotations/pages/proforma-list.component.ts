import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { ProformaStatus, ProformaSummary, STATUS_CLASSES, STATUS_LABELS } from '../models/proforma';
import { ProformasApiService } from '../services/proformas-api.service';

/** Cotizaciones → Proformas: lista con filtros (plantilla Lista del sistema de diseño). */
@Component({
  selector: 'app-proforma-list',
  imports: [ReactiveFormsModule, RouterLink, MoneyPipe],
  templateUrl: './proforma-list.component.html',
})
export class ProformaListComponent implements OnInit {
  private api = inject(ProformasApiService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;

  readonly statuses = Object.keys(STATUS_LABELS) as ProformaStatus[];
  readonly labels = STATUS_LABELS;
  readonly classes = STATUS_CLASSES;
  readonly filters = this.fb.group({ customer: '', from: '', to: '', status: '' });

  rows: ProformaSummary[] = [];
  count = 0;
  page = 1;
  loading = false;
  error = '';

  ngOnInit(): void {
    this.search();
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
    this.loading = true;
    this.error = '';
    this.api.list({ ...raw, status: raw.status as ProformaStatus | '', customer: raw.customer.trim(), page })
      .pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.loading = false))
      .subscribe({
        next: result => { this.rows = result.results; this.count = result.count; },
        error: () => this.error = 'No se pudieron cargar las proformas.',
      });
  }

  clear(): void {
    this.filters.reset();
    this.search();
  }
}
