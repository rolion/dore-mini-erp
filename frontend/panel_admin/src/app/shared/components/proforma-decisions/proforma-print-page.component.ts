import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, ViewEncapsulation, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize } from 'rxjs';
import {
  DecisionFailure, PrintableProforma, acceptanceLabel, decisionLabel,
} from '../../models/proforma-decisions';
import { MoneyPipe } from '../../pipes/money.pipe';
import { ProformaApiBase, ProformaDecisionsApiService } from '../../services/proforma-decisions-api.service';

/**
 * Vista imprimible de una proforma presentada o reemplazada. Muestra solo los datos comerciales que el servidor
 * entrega en `printable/`; «Guardar como PDF» usa el diálogo de impresión del navegador. Se monta bajo
 * `quotations/proformas/:id/imprimir` y `dentistry/proformas/:id/imprimir` con `data: { base }`.
 */
@Component({
  selector: 'app-proforma-print-page',
  imports: [RouterLink, MoneyPipe, DatePipe, TranslatePipe],
  encapsulation: ViewEncapsulation.None,
  template: `
    <section class="main-content proforma-print">
      <div class="no-print d-flex flex-wrap gap-2 mb-3">
        @if (backLink) { <a class="btn btn-light" [routerLink]="backLink">{{ 'PROFORMA_DECISIONS.VOLVER_DETALLE' | translate }}</a> }
        <button type="button" class="btn btn-primary" [disabled]="!data" (click)="print()">{{ 'PROFORMA_DECISIONS.IMPRIMIR_AHORA' | translate }}</button>
      </div>
      @if (loading) { <p role="status">{{ 'PROFORMA_DECISIONS.CARGANDO' | translate }}</p> }
      @if (error) { <p class="alert alert-danger no-print" role="alert">{{ error }}</p> }
      @if (data; as p) {
        <article class="card">
          <div class="card-body">
            <h2>{{ p.number }} · v{{ p.version }}</h2>
            <dl class="row">
              <dt class="col-sm-3">{{ 'PROFORMA_DECISIONS.P_CLIENTE' | translate }}</dt><dd class="col-sm-9">{{ p.customer_name || p.patient_name }}</dd>
              <dt class="col-sm-3">{{ 'PROFORMA_DECISIONS.P_FECHA' | translate }}</dt><dd class="col-sm-9">{{ p.date | date: 'dd/MM/yyyy' }}</dd>
              <dt class="col-sm-3">{{ 'PROFORMA_DECISIONS.P_VIGENCIA' | translate }}</dt><dd class="col-sm-9">{{ (p.valid_until | date: 'dd/MM/yyyy') || '—' }}</dd>
              <dt class="col-sm-3">{{ 'PROFORMA_DECISIONS.P_ESTADO' | translate }}</dt><dd class="col-sm-9">{{ acceptanceLabel(p.acceptance_status) }}</dd>
            </dl>
            <table class="table">
              <thead><tr>
                <th scope="col">{{ 'PROFORMA_DECISIONS.COL_SERVICIO' | translate }}</th>
                <th scope="col" class="text-end">{{ 'PROFORMA_DECISIONS.COL_CANTIDAD' | translate }}</th>
                <th scope="col" class="text-end">{{ 'PROFORMA_DECISIONS.COL_PRECIO' | translate }}</th>
                <th scope="col" class="text-end">{{ 'PROFORMA_DECISIONS.COL_SUBTOTAL' | translate }}</th>
                <th scope="col">{{ 'PROFORMA_DECISIONS.COL_DECISION' | translate }}</th>
              </tr></thead>
              <tbody>
                @for (line of p.lines; track $index) {
                  <tr>
                    <td>{{ line.description }}@if (line.dental_piece || line.piece) { · {{ line.dental_piece || line.piece }} }</td>
                    <td class="text-end">{{ line.quantity }}</td>
                    <td class="text-end">{{ line.unit_price | money }}</td>
                    <td class="text-end">{{ line.subtotal | money }}</td>
                    <td>{{ decisionLabel(line.decision) }}@if (line.decided_at) { · {{ line.decided_at | date: 'dd/MM/yyyy' }} }</td>
                  </tr>
                }
              </tbody>
            </table>
            <dl class="row">
              <dt class="col-sm-3">{{ 'PROFORMA_DECISIONS.TOTAL_PROPUESTO' | translate }}</dt><dd class="col-sm-9">{{ p.totals.proposed | money }}</dd>
              <dt class="col-sm-3">{{ 'PROFORMA_DECISIONS.TOTAL_ACEPTADO' | translate }}</dt><dd class="col-sm-9">{{ p.totals.accepted | money }}</dd>
              <dt class="col-sm-3">{{ 'PROFORMA_DECISIONS.PENDIENTE' | translate }}</dt><dd class="col-sm-9">{{ p.totals.pending | money }}</dd>
              <dt class="col-sm-3">{{ 'PROFORMA_DECISIONS.P_CONDICIONES' | translate }}</dt><dd class="col-sm-9">{{ p.notes || '—' }}</dd>
            </dl>
          </div>
        </article>
      }
    </section>
  `,
  styles: [`
    @media print {
      .proforma-print .no-print,
      app-sidebar, app-header, app-right-sidebar, app-footer, .navbar, .sidebar, .overlay { display: none !important; }
      section.main-content.proforma-print { margin: 0 !important; padding: 0 !important; inset: auto !important; }
    }
  `],
})
export class ProformaPrintPageComponent implements OnInit {
  private api = inject(ProformaDecisionsApiService);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);

  readonly decisionLabel = decisionLabel;
  readonly acceptanceLabel = acceptanceLabel;

  data: PrintableProforma | null = null;
  loading = true;
  error = '';
  backLink: string[] | null = null;

  ngOnInit(): void {
    const base = this.route.snapshot.data['base'] as ProformaApiBase;
    const id = this.route.snapshot.paramMap.get('id') ?? this.route.snapshot.paramMap.get('proformaId') ?? '';
    this.backLink = ['/pocketbiz', base, id];
    this.api.printable(base, id).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.loading = false)).subscribe({
      next: data => this.data = data,
      error: (failure: DecisionFailure) => this.error = failure.message,
    });
  }

  print(): void {
    window.print();
  }
}
