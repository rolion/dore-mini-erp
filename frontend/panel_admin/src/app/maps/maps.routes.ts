import { Route } from "@angular/router";
import { GoogleComponent } from "./google/google.component";
export const MAPS_ROUTE: Route[] = [
  {
    path: "google",
    component: GoogleComponent,
  },
];
