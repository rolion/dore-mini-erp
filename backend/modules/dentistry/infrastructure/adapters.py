from modules.customers.services import get_customers_administrative, search_customer_ids


class CustomersAdapter:
    def __init__(self, company_id):
        self.company_id = company_id

    def get_many(self, ids):
        return get_customers_administrative(self.company_id, ids)

    def search_ids(self, search):
        return search_customer_ids(self.company_id, search)
