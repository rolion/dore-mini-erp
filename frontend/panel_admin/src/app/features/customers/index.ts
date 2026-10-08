// API pública de la feature: lo único que otras features pueden importar.
export type { Customer, CustomerListParams } from './models/customer';
export { CustomerQuickCreateService } from './services/customer-quick-create.service';
export { CustomersApiService } from './services/customers-api.service';
