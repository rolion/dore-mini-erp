import { Route } from "@angular/router";
import { InboxComponent } from "./inbox/inbox.component";
import { ComposeComponent } from "./compose/compose.component";
import { ReadMailComponent } from "./read-mail/read-mail.component";
export const EMAIL_ROUTE: Route[] = [
  {
    path: "inbox",
    component: InboxComponent,
  },
  {
    path: "compose",
    component: ComposeComponent,
  },
  {
    path: "read-mail",
    component: ReadMailComponent,
  },
];
