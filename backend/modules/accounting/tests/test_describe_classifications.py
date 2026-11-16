"""CONT-03: `describe_classifications` solo devuelve clasificaciones de la empresa pedida."""
from django.test import TestCase

from modules.accounting import services
from modules.accounting.infrastructure.django.models import ClassificationModel
from modules.accounts.testing import make_company


class DescribeClassificationsTests(TestCase):
    def setUp(self):
        self.company = make_company('Empresa A')
        self.other = make_company('Empresa B')
        self.rent = ClassificationModel.objects.create(company_id=self.company.id, name='Alquiler', direction='EXPENSE')
        self.sales = ClassificationModel.objects.create(company_id=self.company.id, name='Ventas', direction='INCOME',
                                                        is_active=False)
        self.foreign = ClassificationModel.objects.create(company_id=self.other.id, name='Ajena', direction='EXPENSE')

    def test_returns_name_direction_and_state(self):
        found = services.describe_classifications(self.company.id, [self.rent.id, self.sales.id])
        self.assertEqual(found[self.rent.id], services.ClassificationInfo(self.rent.id, 'Alquiler', 'EXPENSE', True))
        self.assertFalse(found[self.sales.id].is_active)
        self.assertEqual(found[self.sales.id].direction, 'INCOME')

    def test_skips_other_company_unknown_and_empty(self):
        found = services.describe_classifications(self.company.id, [self.foreign.id])
        self.assertEqual(found, {})
        self.assertEqual(services.describe_classifications(self.company.id, []), {})
