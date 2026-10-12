from types import SimpleNamespace
from unittest import TestCase
from uuid import uuid4

from shared.tenancy import MissingCompanyError, company_id_from


class CompanyIdFromTests(TestCase):
    def test_reads_the_company_of_the_authenticated_user(self):  # INV-02
        company_id = uuid4()
        request = SimpleNamespace(user=SimpleNamespace(company_id=company_id))
        self.assertEqual(company_id_from(request), company_id)

    def test_ignores_what_the_client_sends(self):  # INV-02
        request = SimpleNamespace(user=SimpleNamespace(company_id=None), data={'company_id': str(uuid4())},
                                  query_params={'company_id': str(uuid4())})
        with self.assertRaises(MissingCompanyError):
            company_id_from(request)

    def test_request_without_user_fails_explicitly(self):
        with self.assertRaises(MissingCompanyError):
            company_id_from(SimpleNamespace())
