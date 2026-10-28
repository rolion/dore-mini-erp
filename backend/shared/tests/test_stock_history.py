from uuid import uuid4

from django.test import SimpleTestCase

from shared import stock_history


class StockHistoryPortTests(SimpleTestCase):
    def tearDown(self):
        stock_history.register(None)

    def test_without_provider_there_is_no_history(self):
        self.assertFalse(stock_history.has_history(uuid4(), uuid4()))

    def test_registered_provider_answers(self):
        company_id, product_id = uuid4(), uuid4()
        stock_history.register(lambda c, p: (c, p) == (company_id, product_id))
        self.assertTrue(stock_history.has_history(company_id, product_id))
        self.assertFalse(stock_history.has_history(company_id, uuid4()))
