import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { EMPTY } from 'rxjs';
import { NgbTooltip } from '@ng-bootstrap/ng-bootstrap';
import { RouterLink } from '@angular/router';
import { ModulesService } from '../../../../core/service/modules.service';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { OrderStatusBadgeComponent, PaymentStatusBadgeComponent } from '../../../sales';
import { PeriodSelectorComponent } from '../../components/period-selector/period-selector.component';
import { ReportCardComponent, UNAVAILABLE_MESSAGE } from '../../components/report-card/report-card.component';
import { RemoteResource } from '../../models/remote';
import { DEFAULT_SELECTION, DashboardSummary, Period, PeriodSelection } from '../../models/report';
import { ReportingApiService } from '../../services/reporting-api.service';

export const ESTIMATE_NOTE = 'Ventas menos gastos registrados; no incluye costo de producción ni costo de ventas.';
export const PROFIT_REQUIRES_NOTE = 'Requiere Ventas y Gastos habilitados.';
export const PENDING_NOTE = 'Estado actual de todos los pedidos; no depende del periodo.';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  imports: [
    AsyncPipe,
    DatePipe,
    RouterLink,
    NgbTooltip,
    MoneyPipe,
    PeriodSelectorComponent,
    ReportCardComponent,
    OrderStatusBadgeComponent,
    PaymentStatusBadgeComponent,
  ],
})
export class DashboardComponent {
  readonly estimateNote = ESTIMATE_NOTE;
  readonly pendingNote = PENDING_NOTE;
  readonly profitRequires = PROFIT_REQUIRES_NOTE;
  readonly unavailableMessage = UNAVAILABLE_MESSAGE;

  selection: PeriodSelection = DEFAULT_SELECTION;

  private api = inject(ReportingApiService);
  private modules = inject(ModulesService);
  private moneyPipe = new MoneyPipe();

  /** Indicadores del periodo: una sola consulta, que se repite al cambiar el periodo. */
  readonly summary = new RemoteResource(() => this.api.dashboard(this.selection));
  /** Pendientes de entrega y de cobro: estado actual, independiente del periodo. */
  readonly pending = new RemoteResource(() => (this.salesDisabled ? EMPTY : this.api.pending()));

  /** Con Ventas deshabilitado no se pide (ni se muestra) lo pendiente: la tarjeta lo explica. */
  get salesDisabled(): boolean {
    return this.modules.isDisabled('sales');
  }

  onSelection(selection: PeriodSelection): void {
    this.selection = selection;
    this.summary.reload();
  }

  refresh(): void {
    this.summary.reload();
    this.pending.reload();
  }

  /** Periodo efectivo que devolvió el servidor, como `dd/MM/aaaa – dd/MM/aaaa`. */
  periodLabel(period: Period): string {
    return `${this.formatDate(period.dateFrom)} – ${this.formatDate(period.dateTo)}`;
  }

  private formatDate(iso: string): string {
    const [year, month, day] = iso.split('-');
    return `${day}/${month}/${year}`;
  }

  isNegative(amount: string): boolean {
    return amount.startsWith('-');
  }

  /** Fórmula reproducible de la ganancia estimada, con los dos valores del periodo. */
  profitFormula(summary: DashboardSummary): string {
    return `${this.moneyPipe.transform(summary.salesTotal)} − ${this.moneyPipe.transform(summary.expensesTotal)}`;
  }
}
