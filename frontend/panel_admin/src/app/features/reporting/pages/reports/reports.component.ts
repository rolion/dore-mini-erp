import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApexChart, ApexLegend, NgApexchartsModule } from 'ng-apexcharts';
import { SALES_CHANNEL_LABELS, SalesChannel } from '../../../../shared/models/sales-channel';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { PeriodSelectorComponent } from '../../components/period-selector/period-selector.component';
import { ReportCardComponent } from '../../components/report-card/report-card.component';
import { RemoteResource } from '../../models/remote';
import { DEFAULT_SELECTION, ExpensesReport, PeriodSelection } from '../../models/report';
import { ReportingApiService } from '../../services/reporting-api.service';

export const PRODUCT_AMOUNT_NOTE = 'Importes antes de descuentos del pedido.';
export const CUSTOMER_RANKING_NOTE = 'No incluye pedidos sin cliente.';

/** Porcentaje de `part` sobre `total` con un decimal; solo para mostrar (los importes exactos siguen siendo texto). */
export function percentOf(part: string, total: string): number {
  const whole = Number(total);
  return whole > 0 ? Math.round((Number(part) / whole) * 1000) / 10 : 0;
}

@Component({
  selector: 'app-reports',
  templateUrl: './reports.component.html',
  imports: [
    AsyncPipe,
    RouterLink,
    NgApexchartsModule,
    MoneyPipe,
    PeriodSelectorComponent,
    ReportCardComponent,
  ],
})
export class ReportsComponent {
  readonly productAmountNote = PRODUCT_AMOUNT_NOTE;
  readonly customerRankingNote = CUSTOMER_RANKING_NOTE;
  readonly chart: ApexChart = { type: 'donut', height: 260, foreColor: '#9aa0ac' };
  readonly legend: ApexLegend = { position: 'bottom' };

  selection: PeriodSelection = DEFAULT_SELECTION;

  private api = inject(ReportingApiService);

  readonly sales = new RemoteResource(() => this.api.sales(this.selection));
  readonly expenses = new RemoteResource(() => this.api.expenses(this.selection));
  readonly channels = new RemoteResource(() => this.api.salesByChannel(this.selection));
  readonly products = new RemoteResource(() => this.api.topProducts(this.selection));
  readonly customers = new RemoteResource(() => this.api.topCustomers(this.selection));

  private readonly all = [this.sales, this.expenses, this.channels, this.products, this.customers];

  onSelection(selection: PeriodSelection): void {
    this.selection = selection;
    this.all.forEach((resource) => resource.reload());
  }

  channelLabel(code: SalesChannel): string {
    return SALES_CHANNEL_LABELS[code] ?? code;
  }

  /** Suma de los totales por canal (los mismos pedidos válidos que las ventas); solo para calcular porcentajes. */
  channelsTotal(channels: { total: string }[]): string {
    return String(channels.reduce((sum, channel) => sum + Number(channel.total), 0));
  }

  percent(part: string, total: string): number {
    return percentOf(part, total);
  }

  categoryLabel(category: { name: string; active: boolean }): string {
    return category.active ? category.name : `${category.name} (inactiva)`;
  }

  /** Serie de la dona: números solo para dibujar; la tabla de al lado muestra los importes exactos. */
  chartSeries(report: ExpensesReport): number[] {
    return report.categories.map((category) => Number(category.total));
  }

  chartLabels(report: ExpensesReport): string[] {
    return report.categories.map((category) => this.categoryLabel(category));
  }
}
