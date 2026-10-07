import { Route } from "@angular/router";
import { FontAwesomeComponent } from './font-awesome/font-awesome.component';
import { MaterialIconsComponent } from './material-icons/material-icons.component';
import { FeatherIconsComponent } from './feather-icons/feather-icons.component';
export const ICONS_ROUTE: Route[] = [
  {
    path: 'material',
    component: MaterialIconsComponent,
  },
  {
    path: 'font-awesome',
    component: FontAwesomeComponent,
  },
  {
    path: 'feather',
    component: FeatherIconsComponent,
  },
];
