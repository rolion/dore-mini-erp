import { DatePipe } from '@angular/common';
import { Component, DestroyRef, Input, OnChanges, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TranslatePipe } from '@ngx-translate/core';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { tr } from '../../../core/i18n/translate';
import { ModulesService } from '../../../core/service/modules.service';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { DentalProformaSummary, PROFORMA_STATUS_CLASSES, proformaStatusLabel } from '../models/dental-proforma';
import { DentalProformasApiService } from '../services/dental-proformas-api.service';

/** Tarjeta «Proformas» de la ficha del paciente: todas sus proformas de Odontología con su estado. */
@Component({
  selector: 'app-patient-proformas',
  imports: [RouterLink, MoneyPipe, DatePipe, TranslatePipe],
  templateUrl: './patient-proformas.component.html',
})
export class PatientProformasComponent implements OnInit, OnChanges {
  private api = inject(DentalProformasApiService);
  private modules = inject(ModulesService);
  private destroyRef = inject(DestroyRef);

  @Input({ required: true }) patientId = '';
  @Input() active = true;

  readonly statusLabel = proformaStatusLabel;
  readonly classes = PROFORMA_STATUS_CLASSES;

  servicesEnabled = false;
  rows: DentalProformaSummary[] = [];
  count = 0;
  page = 1;
  loading = false;
  error = '';

  ngOnInit(): void {
    this.modules.enabledKeys$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(keys => {
      const enabled = !!keys && keys.has('services');
      if (enabled && !this.servicesEnabled) this.load(1);
      this.servicesEnabled = enabled;
    });
  }

  ngOnChanges(): void {
    if (this.servicesEnabled) this.load(1);
  }

  get pages(): number {
    return Math.max(1, Math.ceil(this.count / 10));
  }

  load(page: number): void {
    if (!this.patientId) return;
    this.page = page;
    this.loading = true;
    this.error = '';
    this.api.listForPatient(this.patientId, { page }).pipe(
      takeUntilDestroyed(this.destroyRef), finalize(() => this.loading = false),
    ).subscribe({
      next: result => { this.rows = result.results; this.count = result.count; },
      error: () => this.error = tr('DENTISTRY.PROFORMAS.ERR_LISTA'),
    });
  }
}
