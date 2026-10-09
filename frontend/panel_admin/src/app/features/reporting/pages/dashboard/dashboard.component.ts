import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { NgbTooltip } from '@ng-bootstrap/ng-bootstrap';
import { RouterLink } from '@angular/router';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { OrderStatusBadgeComponent, PaymentStatusBadgeComponent } from '../../../sales';
import { PeriodSelectorComponent } from '../../components/period-selector/period-selector.component';
import { ReportCardComponent } from '../../components/report-card/report-card.component';
import { RemoteResource } from '../../models/remote';
import { DEFAULT_SELECTION, DashboardSummary, PeriodSelection } from '../../models/report';
import { ReportingApiService } from '../../services/reporting-api.service';

export const ESTIMATE_NOTE = 'Ventas − gastos registrados. Es una estimación, no la utilidad contable.';
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

  selection: PeriodSelection = DEFAULT_SELECTION;

  private api = inject(ReportingApiService);
  private moneyPipe = new MoneyPipe();

  /** Indicadores del periodo: una sola consulta, que se repite al cambiar el periodo. */
  readonly summary = new RemoteResource(() => this.api.dashboard(this.selection));
  /** Pendientes de entrega y de cobro: estado actual, independiente del periodo. */
  readonly pending = new RemoteResource(() => this.api.pending());

  onSelection(selection: PeriodSelection): void {
    this.selection = selection;
    this.summary.reload();
  }

  refresh(): void {
    this.summary.reload();
    this.pending.reload();
  }

  isNegative(amount: string): boolean {
    return amount.startsWith('-');
  }

  /** Fórmula reproducible de la ganancia estimada, con los dos valores del periodo. */
  profitFormula(summary: DashboardSummary): string {
    return `${this.moneyPipe.transform(summary.salesTotal)} − ${this.moneyPipe.transform(summary.expensesTotal)}`;
  }
}
