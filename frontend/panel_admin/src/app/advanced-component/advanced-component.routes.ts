import { Route } from '@angular/router';
import { AvatarComponent } from './avatar/avatar.component';
import { CardComponent } from './card/card.component';
import { SweetAlertComponent } from './sweet-alert/sweet-alert.component';
import { ToastComponent } from './toast/toast.component';

export const ADVANCE_COMPONENT_ROUTE: Route[] = [
  {
    path: 'avatar',
    component: AvatarComponent,
  },
  {
    path: 'card',
    component: CardComponent,
  },
  {
    path: 'sweet-alert',
    component: SweetAlertComponent,
  },
  {
    path: 'toast',
    component: ToastComponent,
  },
];

