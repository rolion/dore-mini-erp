import { Route } from "@angular/router";
import { ChartWidgetComponent } from "./chart-widget/chart-widget.component";
import { DataWidgetComponent } from "./data-widget/data-widget.component";
export const WIDGET_ROUTE: Route[] = [
  {
    path: '',
    redirectTo: 'chart-widget',
    pathMatch: 'full',
  },
  {
    path: 'chart-widget',
    component: ChartWidgetComponent,
  },
  {
    path: 'data-widget',
    component: DataWidgetComponent,
  },
];
