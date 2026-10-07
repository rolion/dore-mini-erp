import { Route } from "@angular/router";
import { ChatComponent } from "./chat/chat.component";
import { ContactGridComponent } from "./contact-grid/contact-grid.component";
import { BlogComponent } from "./blog/blog.component";

export const APPS_ROUTE: Route[] = [
  {
    path: 'chat',
    component: ChatComponent,
  },
  {
    path: 'blog',
    component: BlogComponent,
  },
  {
    path: 'contact-grid',
    component: ContactGridComponent,
  },
];
