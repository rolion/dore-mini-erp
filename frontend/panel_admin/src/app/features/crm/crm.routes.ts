import { Route, Routes } from '@angular/router';
import { CrmBoardComponent } from './pages/crm-board/crm-board.component';
import { CrmCustomerListComponent } from './pages/crm-customer-list/crm-customer-list.component';

export const CRM_CUSTOMERS_ROUTE: Route[] = [{ path: '', component: CrmCustomerListComponent }];

export const CRM_BOARD_ROUTE: Routes = [{ path: '', component: CrmBoardComponent }];
