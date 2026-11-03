from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from modules.accounts.testing import make_admin
from modules.agenda.models import Shift
from modules.modularity.infrastructure.django.repositories import DjangoCompanyModuleRepository
from modules.personnel.infrastructure.django.models import ProfessionalModel


class AgendaApiTests(TransactionTestCase):
    def setUp(self):
        self.admin = make_admin(username='agenda-admin')
        self.other = make_admin(username='agenda-other')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.modules = DjangoCompanyModuleRepository(self.admin.company_id)
        self.modules.enabled_keys()
        self.modules.enable('personnel')
        self.professional = ProfessionalModel.objects.create(
            company_id=self.admin.company_id, name='Ana',
            created_by=self.admin.pk, updated_by=self.admin.pk,
        )
        self.base = f'/api/agenda/{self.professional.pk}/'
        self.shift = {
            'day': 0, 'starts': '09:00', 'ends': '12:00',
            'valid_from': '2026-11-02', 'valid_until': '2026-11-08', 'breaks': [],
        }

    def week(self):
        return self.client.get(self.base + 'week/', {'start': '2026-11-02'})

    def test_permissions_and_company_isolation(self):
        self.assertEqual(self.week().status_code, 403)
        self.modules.enable('agenda')
        self.assertEqual(self.week().status_code, 200)
        self.client.force_authenticate(None)
        self.assertEqual(self.week().status_code, 401)
        modules = DjangoCompanyModuleRepository(self.other.company_id)
        modules.enabled_keys()
        modules.enable('personnel')
        modules.enable('agenda')
        self.client.force_authenticate(self.other)
        self.assertEqual(self.week().status_code, 404)
        self.assertEqual(self.client.post(self.base + 'shifts/', self.shift, format='json').status_code, 404)

    def test_create_edit_and_subtract_pause_and_absence_in_bolivia(self):
        self.modules.enable('agenda')
        created = self.client.post(self.base + 'shifts/', self.shift, format='json')
        self.assertEqual(created.status_code, 201, created.content)
        edited = self.client.put(
            self.base + f"shifts/{created.json()['id']}/",
            {**self.shift, 'breaks': [{'starts': '10:00', 'ends': '10:30'}]}, format='json',
        )
        self.assertEqual(edited.status_code, 200, edited.content)
        absence = self.client.post(
            self.base + 'absences/',
            {'starts': '2026-11-02T14:15:00Z', 'ends': '2026-11-02T15:00:00Z', 'reason': 'Permiso'},
            format='json',
        )
        self.assertEqual(absence.status_code, 201, absence.content)
        self.assertEqual(absence.json()['starts'], '2026-11-02T10:15:00-04:00')
        self.assertEqual(self.week().json()['availability'], [
            {'starts': '2026-11-02T09:00:00-04:00', 'ends': '2026-11-02T10:00:00-04:00'},
            {'starts': '2026-11-02T11:00:00-04:00', 'ends': '2026-11-02T12:00:00-04:00'},
        ])

    def test_concurrent_overlapping_writes_accept_only_one(self):
        self.modules.enable('agenda')
        barrier = Barrier(2, timeout=10)

        def submit():
            client = APIClient()
            client.force_authenticate(self.admin)
            try:
                barrier.wait()
                return client.post(self.base + 'shifts/', self.shift, format='json').status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = [pool.submit(submit) for _ in range(2)]
            self.assertCountEqual([response.result(timeout=20) for response in responses], [201, 400])
        self.assertEqual(Shift.objects.count(), 1)
