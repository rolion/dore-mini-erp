from django.test import TestCase

from modules.accounts.testing import make_company
from modules.crm.infrastructure.django.models import BoardModel, StageModel
from shared import company_defaults


class CrmDefaultsTests(TestCase):
    def test_snapshot_gives_every_company_an_empty_sales_board_idempotently(self):
        company = make_company('Defaults CRM')
        company_defaults.apply_all(company.id)
        company_defaults.apply_all(company.id)
        boards = BoardModel.objects.filter(company_id=company.id)
        self.assertEqual([(b.name, b.is_active) for b in boards], [('Ventas', True)])
        self.assertFalse(StageModel.objects.filter(board__company_id=company.id).exists())

    def test_apply_does_not_touch_other_companies(self):
        a, b = make_company('A'), make_company('B')
        company_defaults.apply_all(a.id)
        self.assertFalse(BoardModel.objects.filter(company_id=b.id).exists())
