from decimal import Decimal
from unittest import TestCase
from uuid import uuid4

from modules.service_catalog.application.services import ServiceCatalog, UnavailableSpecialties
from modules.service_catalog.domain.service import Service, ServiceValidationError


class ServiceDomainTests(TestCase):
    def test_code_normalized_before_length_validation_and_price_decimal(self):
        service = Service.create(name=' Limpieza ', code=' lim-01 ', base_price='120', duration_minutes=30)
        self.assertEqual((service.name, service.code, service.base_price), ('Limpieza', 'LIM-01', Decimal('120.00')))
        self.assertIsInstance(service.base_price, Decimal)
        self.assertEqual(service.updated(code=' abc ').code, 'ABC')

    def test_rejects_invalid_values_without_mutating_existing_service(self):
        service = Service.create(name='Consulta', base_price='120', duration_minutes=30)
        cases = [('name', ''), ('name', ' '), ('name', 'x' * 151), ('code', 'x' * 51),
                 ('description', 'x' * 5001), ('base_price', '-1'), ('base_price', 'NaN'),
                 ('base_price', 'Infinity'), ('base_price', '1.001'), ('base_price', '10000000000'),
                 ('base_price', 1.2), ('base_price', True), ('duration_minutes', 0),
                 ('duration_minutes', -1), ('duration_minutes', 1.5), ('duration_minutes', True),
                 ('duration_minutes', 2147483648)]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                with self.assertRaises(ServiceValidationError) as caught:
                    service.updated(**{field: value})
                self.assertIn(field, caught.exception.errors)
        self.assertEqual((service.base_price, service.duration_minutes), (Decimal('120.00'), 30))

    def test_zero_price_allowed_and_state_methods_preserve_values(self):
        service = Service.create(name='Evaluación', base_price='0', duration_minutes=1)
        service.deactivate()
        self.assertFalse(service.active)
        self.assertEqual((service.base_price, service.duration_minutes), (Decimal('0.00'), 1))
        service.activate()
        self.assertTrue(service.active)

    def test_unverified_specialty_never_reaches_repository(self):
        class Repository:
            def save(self, service):
                raise AssertionError('Must not persist invalid references')
        catalog = ServiceCatalog(Repository(), UnavailableSpecialties())
        with self.assertRaises(ServiceValidationError) as caught:
            catalog.create(name='Consulta', base_price='120', duration_minutes=30, specialty_id=uuid4())
        self.assertIn('specialty_id', caught.exception.errors)
