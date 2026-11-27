import { Route, Routes } from '@angular/router';
import { CrmBoardComponent } from './pages/crm-board/crm-board.component';
import { CrmCustomerListComponent } from './pages/crm-customer-list/crm-customer-list.component';
import { CrmLeadListComponent } from './pages/crm-lead-list/crm-lead-list.component';
import { CrmTaskListComponent } from './pages/crm-task-list/crm-task-list.component';
import { CrmTrackingBoardListComponent } from './pages/crm-tracking-board-list/crm-tracking-board-list.component';
import { CrmTrackingBoardComponent } from './pages/crm-tracking-board/crm-tracking-board.component';
import { CrmOpportunityBoardComponent } from './pages/crm-opportunity-board/crm-opportunity-board.component';

export const CRM_CUSTOMERS_ROUTE: Route[] = [{ path: '', component: CrmCustomerListComponent }];

export const CRM_BOARD_ROUTE: Routes = [{ path: '', component: CrmBoardComponent }];

export const CRM_OPPORTUNITIES_ROUTE: Routes = [{ path: '', component: CrmOpportunityBoardComponent }];

export const CRM_LEADS_ROUTE: Routes = [{ path: '', component: CrmLeadListComponent }];

export const CRM_TASKS_ROUTE: Routes = [{ path: '', component: CrmTaskListComponent }];

export const CRM_TRACKING_ROUTE: Routes = [
  { path: '', component: CrmTrackingBoardListComponent },
  { path: ':boardId', component: CrmTrackingBoardComponent },
];
