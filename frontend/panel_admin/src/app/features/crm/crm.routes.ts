import { Route, Routes } from '@angular/router';
import { CrmBoardComponent } from './pages/crm-board/crm-board.component';
import { CrmCustomerListComponent } from './pages/crm-customer-list/crm-customer-list.component';
import { CrmLeadListComponent } from './pages/crm-lead-list/crm-lead-list.component';
import { CrmOpportunityBoardComponent } from './pages/crm-opportunity-board/crm-opportunity-board.component';

export const CRM_CUSTOMERS_ROUTE: Route[] = [{ path: '', component: CrmCustomerListComponent }];

export const CRM_BOARD_ROUTE: Routes = [{ path: '', component: CrmBoardComponent }];

export const CRM_OPPORTUNITIES_ROUTE: Routes = [{ path: '', component: CrmOpportunityBoardComponent }];

export const CRM_LEADS_ROUTE: Routes = [{ path: '', component: CrmLeadListComponent }];
