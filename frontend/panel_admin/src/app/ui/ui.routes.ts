import { AlertsComponent } from './alerts/alerts.component';
import { Route } from '@angular/router';
import { BadgesComponent } from './badges/badges.component';
import { ButtonsComponent } from './buttons/buttons.component';
import { CollapseComponent } from './collapse/collapse.component';
import { DropdownComponent } from './dropdown/dropdown.component';
import { ListComponent } from './list/list.component';
import { ModalsComponent } from './modals/modals.component';
import { DatepickerComponent } from './datepicker/datepicker.component';
import { PaginationComponent } from './pagination/pagination.component';
import { ProgressbarsComponent } from './progressbars/progressbars.component';
import { AccordionComponent } from './accordion/accordion.component';
import { TabsComponent } from './tabs/tabs.component';
import { TimepickerComponent } from './timepicker/timepicker.component';
import { RatingsComponent } from './ratings/ratings.component';
import { TooltipComponent } from './tooltip/tooltip.component';
import { CarouselComponent } from './carousel/carousel.component';
import { PopoverComponent } from './popover/popover.component';
import { TypeaheadComponent } from './typeahead/typeahead.component';
import { TypographyComponent } from './typography/typography.component';
export const UI_ROUTE: Route[] = [
  {
    path: 'alerts',
    component: AlertsComponent,
  },
  {
    path: 'badges',
    component: BadgesComponent,
  },
  {
    path: 'buttons',
    component: ButtonsComponent,
  },
  {
    path: 'collapse',
    component: CollapseComponent,
  },
  {
    path: 'dropdown',
    component: DropdownComponent,
  },
  {
    path: 'list',
    component: ListComponent,
  },
  {
    path: 'modals',
    component: ModalsComponent,
  },
  {
    path: 'datepicker',
    component: DatepickerComponent,
  },
  {
    path: 'pagination',
    component: PaginationComponent,
  },
  {
    path: 'progressbars',
    component: ProgressbarsComponent,
  },
  {
    path: 'accordion',
    component: AccordionComponent,
  },
  {
    path: 'tabs',
    component: TabsComponent,
  },
  {
    path: 'timepicker',
    component: TimepickerComponent,
  },
  {
    path: 'ratings',
    component: RatingsComponent,
  },
  {
    path: 'tooltip',
    component: TooltipComponent,
  },
  {
    path: 'carousel',
    component: CarouselComponent,
  },
  {
    path: 'popover',
    component: PopoverComponent,
  },
  {
    path: 'typeahead',
    component: TypeaheadComponent,
  },
  {
    path: 'typography',
    component: TypographyComponent,
  },
];
