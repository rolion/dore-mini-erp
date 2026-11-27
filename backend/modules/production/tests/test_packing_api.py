from decimal import Decimal
from uuid import uuid4

from django.utils import timezone
from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.catalog.infrastructure.django.models import ProductModel
from modules.costing import services as costing_services
from modules.costing.domain.valuation import ValuationAdoption, parse_lines
from modules.costing.infrastructure.django.repositories import DjangoAdoptionRepository
from modules.inventory import services as inventory_services
from modules.inventory.infrastructure.django.models import StockMovementModel
from modules.modularity.infrastructure.django.models import CompanyModuleModel
from modules.production.infrastructure.django.models import PackingModel, ProductionOrderModel

from . import test_order_api as base

URL = base.URL


class OrderPackApiTests(APITestCase):
    """Empaque de packs de 6 (TASK-empacar-bolsas-de-6-venta-detalle). Reutiliza los ayudantes de `OrderApiTests`
    sin heredar sus pruebas."""

    setUp = base.OrderApiTests.setUp
    enable = base.OrderApiTests.enable
    product = base.OrderApiTests.product
    payload = base.OrderApiTests.payload
    create = base.OrderApiTests.create
    order_payload = base.OrderApiTests.order_payload
    make_order = base.OrderApiTests.make_order
    prepare_stock = base.OrderApiTests.prepare_stock
    started_order = base.OrderApiTests.started_order
    refrigerate_payload = base.OrderApiTests.refrigerate_payload
    refrigerate = base.OrderApiTests.refrigerate

    def ready(self, bags='10'):
        """Orden lista para empacar con 118 cuñapés liberados, 10 bolsas y un producto pack."""
        self.prepare_stock()
        self.pack_product = self.product('Pack x6', self.unit)
        self.bag = self.product('Bolsa', self.unit)
        ProductModel.objects.filter(pk__in=[self.pack_product.pk, self.bag.pk]).update(tracks_stock=True)
        inventory_services.record_movement(
            self.company.id, product_id=self.bag.id, warehouse_id=self.warehouse.id, kind='in',
            quantity=Decimal(bags), user_id=self.user.id, user_name='prod-admin', reference='Seed')
        order = self.started_order()
        self.assertEqual(self.refrigerate(order).status_code, 200)
        ProductionOrderModel.objects.filter(pk=order['id']).update(
            entered_at=timezone.now() - timezone.timedelta(hours=13))
        self.assertEqual(self.client.post(f"{URL}{order['id']}/release/").status_code, 200)
        return order

    def add_label(self, quantity='10'):
        """Producto etiqueta con stock en el almacén de la orden."""
        self.label = self.product('Etiqueta', self.unit)
        ProductModel.objects.filter(pk=self.label.pk).update(tracks_stock=True)
        inventory_services.record_movement(
            self.company.id, product_id=self.label.id, warehouse_id=self.warehouse.id, kind='in',
            quantity=Decimal(quantity), user_id=self.user.id, user_name='prod-admin', reference='Seed etiquetas')

    def body(self, packs=6, **changes):
        body = {'request_id': str(uuid4()), 'packs': packs, 'pack_product_id': str(self.pack_product.id),
                'bag_product_id': str(self.bag.id)}
        body.update(changes)
        return body

    def pack(self, order, body=None):
        return self.client.post(f"{URL}{order['id']}/pack/", body or self.body(), format='json')

    def balances(self, order):
        lot = inventory_services.get_lot(self.company.id, self.client.get(f"{URL}{order['id']}/").json()['lot']['id'])
        warehouse = self.warehouse.id
        unlotted = inventory_services.get_balances(
            self.company.id, warehouse, [self.bag.id, self.pack_product.id], unlotted=True)
        return lot.available_quantity, unlotted[self.bag.id], unlotted[self.pack_product.id]

    def movements(self):
        return StockMovementModel.objects.filter(company_id=self.company.id).count()

    def test_pack_moves_stock_from_lot_and_bags_into_packs(self):  # AC-01, INV-02
        order = self.ready()
        response = self.pack(order)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.balances(order), (Decimal('82'), Decimal('4'), Decimal('6')))
        packing = response.json()['packing']
        self.assertEqual(packing['bulk_available'], '82.0000')
        self.assertEqual([(p['number'], p['packs'], p['bulk_quantity'], p['bags_quantity'], p['lot']['code'])
                          for p in packing['packings']], [(1, 6, '36.0000', '6.0000', response.json()['lot']['code'])])
        self.assertEqual(StockMovementModel.objects.filter(
            source_type='production_packing', source_id=packing['packings'][0]['id']).count(), 3)

    def test_shortage_lists_everything_and_changes_nothing(self):  # AC-02, INV-04
        order = self.ready(bags='2')
        before, count = (self.balances(order), self.movements()), PackingModel.objects.count()
        response = self.pack(order, self.body(packs=20))  # 120 cuñapés (hay 118) y 20 bolsas (hay 2)
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json()['code'], 'insufficient_stock')
        self.assertEqual({s['product_name']: (s['requested'], s['available'], s['missing'])
                          for s in response.json()['shortages']},
                         {'Cuñapé a granel': ('120.0000', '118.0000', '2.0000'),
                          'Bolsa': ('20.0000', '2.0000', '18.0000')})
        self.assertEqual(((self.balances(order), self.movements()), PackingModel.objects.count()), (before, count))

    def test_retry_with_same_request_id_does_not_duplicate(self):  # AC-03, INV-05, EDGE-01
        order = self.ready()
        body = self.body()
        first = self.pack(order, body)
        moves = self.movements()
        again = self.pack(order, body)
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertEqual((self.movements(), PackingModel.objects.count()), (moves, 1))
        self.assertEqual(again.json()['packing']['packings'], first.json()['packing']['packings'])

    def test_several_batches_show_history_and_remaining_bulk(self):  # AC-04
        order = self.ready()
        self.assertEqual(self.pack(order, self.body(packs=2)).status_code, 201)
        response = self.pack(order, self.body(packs=3))
        self.assertEqual(response.status_code, 201, response.content)
        detail = self.client.get(f"{URL}{order['id']}/").json()['packing']
        self.assertEqual((detail['bulk_available'], [p['number'] for p in detail['packings']],
                          [p['packs'] for p in detail['packings']]), ('88.0000', [1, 2], [2, 3]))
        self.assertEqual(self.balances(order), (Decimal('88'), Decimal('5'), Decimal('5')))

    def test_pack_cost_uses_average_cost(self):  # AC-05, INV-07
        order_cost = self.ready()
        CompanyModuleModel.objects.create(company_id=self.company.id, module_key='costing')
        lines = parse_lines([
            {'product_id': self.cheese.id, 'reconciled_quantity': '20', 'total_value': '200.00',
             'declared_zero': False, 'source': None},
            {'product_id': self.flour.id, 'reconciled_quantity': '30', 'total_value': '60.00',
             'declared_zero': False, 'source': None},
            {'product_id': self.result.id, 'reconciled_quantity': '118', 'total_value': '118.00',
             'declared_zero': False, 'source': None},
            {'product_id': self.bag.id, 'reconciled_quantity': '10', 'total_value': '5.00',
             'declared_zero': False, 'source': None}])
        DjangoAdoptionRepository(self.company.id).save(
            ValuationAdoption.adopt(uuid4(), timezone.now(), None, 'ana', lines))
        response = self.pack(order_cost)  # 36 × 1.00 + 6 × 0.50 = 39.00 → 6.50 por pack
        self.assertEqual(response.status_code, 201, response.content)
        packing = response.json()['packing']['packings'][0]
        self.assertEqual((packing['cost_total'], packing['unit_cost']), ('39.00', '6.500000'))
        self.assertEqual(costing_services.get_average_costs(self.company.id, [self.pack_product.id]),
                         {self.pack_product.id: Decimal('6.500000')})

    def test_pack_without_costing_keeps_cost_empty(self):  # AC-05, INV-07
        packing = self.pack(self.ready()).json()['packing']['packings'][0]
        self.assertEqual((packing['cost_total'], packing['unit_cost']), (None, None))

    def test_pack_requires_a_ready_order_and_isolation(self):  # AC-06, INV-01
        order = self.ready()
        other_order = self.started_order()
        self.assertEqual(self.pack(other_order).status_code, 409)
        self.assertIsNone(self.client.get(f"{URL}{other_order['id']}/").json()['packing'])
        other = make_company('Producción B')
        authenticate(self.client, make_admin(other, username='other-admin'))
        self.assertEqual(self.pack(order).status_code, 403)  # módulo no habilitado
        self.enable(other)
        self.assertEqual(self.pack(order).status_code, 404)

    def test_invalid_input_is_rejected_by_field(self):  # AC-07, INV-03
        order = self.ready()
        untracked = self.product('Sin stock', self.unit)
        inactive = self.product('Inactivo', self.unit)
        ProductModel.objects.filter(pk=inactive.pk).update(active=False, tracks_stock=True)
        cases = [
            ('packs', self.body(packs=0)), ('packs', self.body(packs=2.5)), ('packs', self.body(packs='x')),
            ('packs', self.body(packs=None)),
            ('pack_product_id', self.body(pack_product_id=str(uuid4()))),
            ('pack_product_id', self.body(pack_product_id=str(inactive.id))),
            ('pack_product_id', self.body(pack_product_id=str(self.result.id))),
            ('pack_product_id', self.body(pack_product_id=str(untracked.id))),
            ('bag_product_id', self.body(bag_product_id=str(self.pack_product.id))),
            ('request_id', self.body(request_id='no-uuid')),
        ]
        moves = self.movements()
        for field, body in cases:
            with self.subTest(field=field, body=body):
                response = self.pack(order, body)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(field, response.json())
        self.assertEqual((self.movements(), PackingModel.objects.count()), (moves, 0))

    def test_label_is_consumed_when_chosen(self):  # AC-09, INV-08
        order = self.ready()
        self.add_label('10')
        response = self.pack(order, self.body(label_product_id=str(self.label.id)))
        self.assertEqual(response.status_code, 201, response.content)
        packing = response.json()['packing']['packings'][0]
        self.assertEqual((packing['label_product']['name'], packing['labels_quantity']), ('Etiqueta', '6.0000'))
        unlotted = inventory_services.get_balances(
            self.company.id, self.warehouse.id, [self.label.id, self.bag.id], unlotted=True)
        self.assertEqual((unlotted[self.label.id], unlotted[self.bag.id]), (Decimal('4'), Decimal('4')))
        self.assertEqual(StockMovementModel.objects.filter(
            source_type='production_packing', source_id=packing['id']).count(), 4)

    def test_without_label_nothing_is_consumed_for_it(self):  # AC-09
        order = self.ready()
        self.add_label('10')
        packing = self.pack(order).json()['packing']['packings'][0]
        self.assertEqual((packing['label_product'], packing['labels_quantity']), (None, '0.0000'))
        self.assertEqual(inventory_services.get_balances(
            self.company.id, self.warehouse.id, [self.label.id], unlotted=True)[self.label.id], Decimal('10'))

    def test_missing_labels_are_listed_with_the_other_shortages(self):  # AC-09, INV-04
        order = self.ready(bags='2')
        self.add_label('1')
        before, count = (self.balances(order), self.movements()), PackingModel.objects.count()
        response = self.pack(order, self.body(packs=5, label_product_id=str(self.label.id)))
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual({s['product_name']: (s['requested'], s['available'], s['missing'])
                          for s in response.json()['shortages']},
                         {'Bolsa': ('5.0000', '2.0000', '3.0000'), 'Etiqueta': ('5.0000', '1.0000', '4.0000')})
        self.assertEqual(((self.balances(order), self.movements()), PackingModel.objects.count()), (before, count))

    def test_invalid_label_is_rejected(self):  # AC-09, INV-08
        order = self.ready()
        untracked = self.product('Etiqueta sin stock', self.unit)
        for label_id in (str(uuid4()), str(untracked.id), str(self.bag.id), str(self.pack_product.id)):
            with self.subTest(label=label_id):
                response = self.pack(order, self.body(label_product_id=label_id))
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn('label_product_id', response.json())
        self.assertEqual(PackingModel.objects.count(), 0)

    def test_label_cost_is_part_of_the_pack_cost(self):  # AC-09, INV-07
        order = self.ready()
        self.add_label('20')
        CompanyModuleModel.objects.create(company_id=self.company.id, module_key='costing')
        lines = parse_lines([
            {'product_id': self.cheese.id, 'reconciled_quantity': '20', 'total_value': '200.00',
             'declared_zero': False, 'source': None},
            {'product_id': self.flour.id, 'reconciled_quantity': '30', 'total_value': '60.00',
             'declared_zero': False, 'source': None},
            {'product_id': self.result.id, 'reconciled_quantity': '118', 'total_value': '118.00',
             'declared_zero': False, 'source': None},
            {'product_id': self.bag.id, 'reconciled_quantity': '10', 'total_value': '5.00',
             'declared_zero': False, 'source': None},
            {'product_id': self.label.id, 'reconciled_quantity': '20', 'total_value': '2.00',
             'declared_zero': False, 'source': None}])
        DjangoAdoptionRepository(self.company.id).save(
            ValuationAdoption.adopt(uuid4(), timezone.now(), None, 'ana', lines))
        response = self.pack(order, self.body(label_product_id=str(self.label.id)))  # 36 + 3.00 + 0.60 = 39.60
        self.assertEqual(response.status_code, 201, response.content)
        packing = response.json()['packing']['packings'][0]
        self.assertEqual((packing['cost_total'], packing['unit_cost']), ('39.60', '6.600000'))

    def add_roll(self, meters='15'):
        """Rollo de bolsa que se lleva en metros (unidad fraccionable)."""
        self.roll = self.product('Bolsa 20cm Ancho', self.kilo)
        ProductModel.objects.filter(pk=self.roll.pk).update(tracks_stock=True)
        inventory_services.record_movement(
            self.company.id, product_id=self.roll.id, warehouse_id=self.warehouse.id, kind='in',
            quantity=Decimal(meters), user_id=self.user.id, user_name='prod-admin', reference='Seed rollo')

    def test_bag_length_per_pack_is_consumed_from_the_roll(self):  # AC-10, INV-02
        order = self.ready()
        self.add_roll('15')
        body = self.body(bag_product_id=str(self.roll.id), bag_per_pack='0.17')
        response = self.pack(order, body)
        self.assertEqual(response.status_code, 201, response.content)
        packing = response.json()['packing']['packings'][0]
        self.assertEqual((packing['bag_per_pack'], packing['bags_quantity']), ('0.1700', '1.0200'))
        self.assertEqual(inventory_services.get_balances(
            self.company.id, self.warehouse.id, [self.roll.id], unlotted=True)[self.roll.id], Decimal('13.98'))
        self.assertEqual(response.json()['packing']['suggested_bag_per_pack'], '0.1700')

    def test_roll_shortage_uses_the_scaled_quantity(self):  # AC-10, INV-04
        order = self.ready()
        self.add_roll('1')
        response = self.pack(order, self.body(bag_product_id=str(self.roll.id), bag_per_pack='0.17'))
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual([(s['product_name'], s['requested'], s['available'], s['missing'])
                          for s in response.json()['shortages']], [('Bolsa 20cm Ancho', '1.0200', '1.0000', '0.0200')])

    def test_invalid_bag_length_is_rejected(self):  # AC-10
        order = self.ready()
        for bad in (0, -0.5, 'x', 0.12345, True):
            with self.subTest(bad=bad):
                response = self.pack(order, self.body(bag_per_pack=bad))
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn('bag_per_pack', response.json())
        self.assertEqual(PackingModel.objects.count(), 0)
