from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from modules.accounts.testing import make_admin, make_company
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

    def test_user_without_active_company_is_rejected(self):
        self.modules.enable('agenda')
        orphan = make_admin(username='agenda-orphan')
        orphan.company = None
        orphan.save()
        inactive = make_admin(make_company('Inactiva', is_active=False), username='agenda-inactive')
        for user in (orphan, inactive):
            self.client.force_authenticate(user)
            self.assertEqual(self.week().status_code, 403)
            self.assertEqual(self.client.post(self.base + 'shifts/', self.shift, format='json').status_code, 403)

    def test_foreign_shift_is_not_found(self):
        self.modules.enable('agenda')
        created = self.client.post(self.base + 'shifts/', self.shift, format='json').json()
        self.assertEqual(self.client.put(self.base + 'shifts/999999/', self.shift, format='json').status_code, 404)
        other_pro = ProfessionalModel.objects.create(
            company_id=self.admin.company_id, name='Luis', created_by=self.admin.pk, updated_by=self.admin.pk,
        )
        response = self.client.put(
            f"/api/agenda/{other_pro.pk}/shifts/{created['id']}/", self.shift, format='json',
        )
        self.assertEqual(response.status_code, 404)

    def test_rejects_invalid_breaks_and_overnight_shift(self):
        self.modules.enable('agenda')
        bad_break = {**self.shift, 'breaks': [{'starts': '08:00', 'ends': '09:30'}]}
        self.assertEqual(self.client.post(self.base + 'shifts/', bad_break, format='json').status_code, 400)
        overnight = {**self.shift, 'starts': '22:00', 'ends': '02:00'}
        self.assertEqual(self.client.post(self.base + 'shifts/', overnight, format='json').status_code, 400)
        self.assertEqual(Shift.objects.count(), 0)

    def test_contiguous_shifts_and_adjacent_validities_are_accepted_but_overlap_is_rejected(self):
        self.modules.enable('agenda')
        post = lambda body: self.client.post(self.base + 'shifts/', body, format='json').status_code
        self.assertEqual(post(self.shift), 201)
        self.assertEqual(post({**self.shift, 'starts': '12:00', 'ends': '13:00'}), 201)
        self.assertEqual(post({**self.shift, 'valid_from': '2026-11-09', 'valid_until': '2026-11-15'}), 201)
        self.assertEqual(post({**self.shift, 'starts': '11:00', 'ends': '13:00'}), 400)
        self.assertEqual(Shift.objects.count(), 3)

    def test_multiday_and_overlapping_absences_in_week(self):
        self.modules.enable('agenda')
        self.assertEqual(self.client.post(self.base + 'shifts/', self.shift, format='json').status_code, 201)
        post = lambda start, end: self.client.post(
            self.base + 'absences/', {'starts': start, 'ends': end, 'reason': 'Viaje'}, format='json',
        ).status_code
        self.assertEqual(post('2026-11-02T10:00:00-04:00', '2026-11-02T11:00:00-04:00'), 201)
        self.assertEqual(post('2026-11-02T10:30:00-04:00', '2026-11-02T11:30:00-04:00'), 201)
        self.assertEqual(post('2026-11-02T12:00:00-04:00', '2026-11-02T11:00:00-04:00'), 400)
        self.assertEqual(self.week().json()['availability'], [
            {'starts': '2026-11-02T09:00:00-04:00', 'ends': '2026-11-02T10:00:00-04:00'},
            {'starts': '2026-11-02T11:30:00-04:00', 'ends': '2026-11-02T12:00:00-04:00'},
        ])
        self.assertEqual(post('2026-11-01T20:00:00-04:00', '2026-11-03T08:00:00-04:00'), 201)
        self.assertEqual(self.week().json()['availability'], [])

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

    def multi(self, **extra):
        body = {key: value for key, value in self.shift.items() if key != 'day'}
        return self.client.post(self.base + 'shifts/', {**body, 'days': [0, 1, 2], **extra}, format='json')

    def test_multiple_days_create_one_shift_per_day(self):
        self.modules.enable('agenda')
        response = self.multi(breaks=[{'starts': '10:00', 'ends': '10:30'}])
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual([item['day'] for item in response.json()], [0, 1, 2])
        self.assertEqual(Shift.objects.count(), 3)
        self.assertTrue(all(len(shift.breaks) == 1 for shift in Shift.objects.all()))

    def test_multiple_days_are_all_or_nothing_on_overlap(self):
        self.modules.enable('agenda')
        self.client.post(self.base + 'shifts/', {**self.shift, 'day': 1}, format='json')
        response = self.multi()
        self.assertEqual(response.status_code, 400)
        self.assertIn('martes', response.json()['starts'][0])
        self.assertEqual(Shift.objects.count(), 1)

    def test_single_day_still_works_and_day_with_days_is_rejected(self):
        self.modules.enable('agenda')
        single = self.client.post(self.base + 'shifts/', self.shift, format='json')
        self.assertEqual((single.status_code, single.json()['day']), (201, 0))
        self.assertEqual(self.client.post(self.base + 'shifts/', {**self.shift, 'days': [1]}, format='json').status_code, 400)
        body = {key: value for key, value in self.shift.items() if key != 'day'}
        self.assertEqual(self.client.post(self.base + 'shifts/', body, format='json').status_code, 400)
        edited = self.client.put(self.base + f"shifts/{single.json()['id']}/", {**self.shift, 'days': [1]}, format='json')
        self.assertEqual(edited.status_code, 400)

    def test_invalid_days_are_rejected(self):
        self.modules.enable('agenda')
        for days in ([], [7], [-1], [1, 1], ['1'], 'x', [True]):
            self.assertEqual(self.multi(days=days).status_code, 400, days)
        self.assertEqual(Shift.objects.count(), 0)

    def test_absence_can_be_edited_and_deleted(self):
        self.modules.enable('agenda')
        self.client.post(self.base + 'shifts/', self.shift, format='json')
        created = self.client.post(
            self.base + 'absences/',
            {'starts': '2026-11-02T10:00:00-04:00', 'ends': '2026-11-02T11:00:00-04:00', 'reason': 'Viaje'},
            format='json',
        ).json()
        url = self.base + f"absences/{created['id']}/"
        edited = self.client.put(
            url, {'starts': '2026-11-02T09:00:00-04:00', 'ends': '2026-11-02T10:00:00-04:00', 'reason': 'Curso'},
            format='json',
        )
        self.assertEqual((edited.status_code, edited.json()['reason']), (200, 'Curso'))
        self.assertEqual(self.week().json()['availability'], [
            {'starts': '2026-11-02T10:00:00-04:00', 'ends': '2026-11-02T12:00:00-04:00'},
        ])
        invalid = self.client.put(
            url, {'starts': '2026-11-02T12:00:00-04:00', 'ends': '2026-11-02T11:00:00-04:00', 'reason': 'x'},
            format='json',
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertEqual(self.week().json()['availability'], [
            {'starts': '2026-11-02T09:00:00-04:00', 'ends': '2026-11-02T12:00:00-04:00'},
        ])

    def test_foreign_absence_is_not_found(self):
        self.modules.enable('agenda')
        created = self.client.post(
            self.base + 'absences/',
            {'starts': '2026-11-02T10:00:00-04:00', 'ends': '2026-11-02T11:00:00-04:00', 'reason': 'Viaje'},
            format='json',
        ).json()
        other_pro = ProfessionalModel.objects.create(
            company_id=self.admin.company_id, name='Luis', created_by=self.admin.pk, updated_by=self.admin.pk,
        )
        foreign = f"/api/agenda/{other_pro.pk}/absences/{created['id']}/"
        body = {'starts': '2026-11-02T10:00:00-04:00', 'ends': '2026-11-02T11:00:00-04:00', 'reason': 'x'}
        self.assertEqual(self.client.put(foreign, body, format='json').status_code, 404)
        self.assertEqual(self.client.delete(foreign).status_code, 404)
        modules = DjangoCompanyModuleRepository(self.other.company_id)
        modules.enabled_keys()
        modules.enable('personnel')
        modules.enable('agenda')
        self.client.force_authenticate(self.other)
        own = self.base + f"absences/{created['id']}/"
        self.assertEqual(self.client.delete(own).status_code, 404)

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
