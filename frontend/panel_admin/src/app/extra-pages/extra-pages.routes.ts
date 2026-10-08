import { Route } from "@angular/router";
import { ProfileComponent } from "./profile/profile.component";
import { PricingComponent } from "./pricing/pricing.component";
import { InvoiceComponent } from "./invoice/invoice.component";
import { FaqsComponent } from "./faqs/faqs.component";
import { BlankComponent } from "./blank/blank.component";
export const EXTRA_PAGES_ROUTE: Route[] = [
  {
    path: 'profile',
    component: ProfileComponent,
  },
  {
    path: 'pricing',
    component: PricingComponent,
  },
  {
    path: 'invoice',
    component: InvoiceComponent,
  },
  {
    path: 'faqs',
    component: FaqsComponent,
  },
  {
    path: 'blank',
    component: BlankComponent,
  },
];
