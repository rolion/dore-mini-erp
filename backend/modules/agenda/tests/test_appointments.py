from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from django.db import connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from modules.accounts.testing import make_admin
from modules.agenda.models import Appointment, AppointmentEvent
from modules.customers.infrastructure.django.models import CustomerModel
from modules.modularity.infrastructure.django.repositories import DjangoCompanyModuleRepository
from modules.personnel.infrastructure.django.models import ProfessionalModel
from modules.service_catalog.infrastructure.django.models import ServiceModel

FUTURE = '2030-01-07'  # lunes
PAST = '2026-10-05'  # lunes anterior a la fecha de las pruebas
SLOT = '-04:00'


def at(day, time):
    return f'{day}T{time}:00{SLOT}'


class AppointmentApiTests(TransactionTestCase):
    def setUp(self):
        self.admin = make_admin(username='appt-admin')
        self.other = make_admin(username='appt-other')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.modules = DjangoCompanyModuleRepository(self.admin.company_id)
        self.modules.enabled_keys()
        for key in ('personnel', 'catalog', 'services', 'agenda'):
            self.modules.enable(key)
        company = self.admin.company_id
        self.pro = ProfessionalModel.objects.create(
            company_id=company, name='Ana', created_by=self.admin.pk, updated_by=self.admin.pk)
        self.customer = CustomerModel.objects.create(company_id=company, name='Rosa Pérez')
        self.service = ServiceModel.objects.create(
            company_id=company, name='Limpieza', base_price=Decimal('100.00'), duration_minutes=30)
        for day, until in ((FUTURE, '2030-01-13'), (PAST, '2026-10-11')):
            response = self.client.post(f'/api/agenda/{self.pro.pk}/shifts/', {
                'day': 0, 'starts': '09:00', 'ends': '12:00', 'valid_from': day, 'valid_until': until,
                'breaks': [{'starts': '10:00', 'ends': '10:30'}],
            }, format='json')
            self.assertEqual(response.status_code, 201, response.content)

    def body(self, day=FUTURE, time='09:00', minutes=30, **extra):
        return {
            'professional_id': str(self.pro.pk), 'customer_id': str(self.customer.pk),
            'service_id': str(self.service.pk), 'starts': at(day, time), 'duration_minutes': minutes, **extra,
        }

    def create(self, **kwargs):
        return self.client.post('/api/agenda/appointments/', self.body(**kwargs), format='json')

    def act(self, appointment_id, action, body=None):
        return self.client.post(f'/api/agenda/appointments/{appointment_id}/{action}/', body or {}, format='json')

    # AC-01
    def test_create_scheduled_and_rejections(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual((data['status'], data['customer_name'], data['service_name']),
                         ('scheduled', 'Rosa Pérez', 'Limpieza'))
        self.assertEqual(data['ends'], at(FUTURE, '09:30'))
        self.assertEqual(data['history'][0]['kind'], 'created')
        for bad in (self.create(time='08:30'), self.create(time='10:15'), self.create(time='11:45'),
                    self.create(minutes=0), self.create(day='2030-01-08')):
            self.assertEqual(bad.status_code, 400, bad.content)
        self.customer.active = False
        self.customer.save()
        self.assertEqual(self.create(time='11:00').status_code, 400)
        self.customer.active = True
        self.customer.save()
        self.service.active = False
        self.service.save()
        self.assertEqual(self.create(time='11:00').status_code, 400)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_foreign_references_and_company_isolation(self):
        foreign = CustomerModel.objects.create(company_id=self.other.company_id, name='Ajeno')
        self.assertEqual(self.create(customer_id=str(foreign.pk)).status_code, 400)
        created = self.create().json()
        modules = DjangoCompanyModuleRepository(self.other.company_id)
        modules.enabled_keys()
        for key in ('personnel', 'catalog', 'services', 'agenda'):
            modules.enable(key)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/agenda/appointments/{created['id']}/").status_code, 404)
        self.assertEqual(self.act(created['id'], 'confirm').status_code, 404)
        self.assertEqual(self.client.get('/api/agenda/appointments/').json()['results'], [])

    def test_module_disabled_is_rejected(self):
        self.modules.disable('services')
        response = self.client.get('/api/agenda/appointments/')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'module_disabled')

    # AC-02
    def test_concurrent_requests_accept_only_one(self):
        barrier = Barrier(2, timeout=10)

        def submit():
            client = APIClient()
            client.force_authenticate(self.admin)
            try:
                barrier.wait()
                return client.post('/api/agenda/appointments/', self.body(), format='json').status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(submit) for _ in range(2)]
            self.assertCountEqual([future.result(timeout=20) for future in futures], [201, 409])
        self.assertEqual(Appointment.objects.count(), 1)

    # AC-03
    def test_contiguous_appointments_are_valid_and_partial_overlap_is_not(self):
        self.assertEqual(self.create(time='09:00').status_code, 201)
        self.assertEqual(self.create(time='09:30').status_code, 201)
        self.assertEqual(self.create(time='09:15').status_code, 409)

    # AC-04
    def test_confirm_keeps_occupying_horario(self):
        created = self.create().json()
        confirmed = self.act(created['id'], 'confirm')
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()['status'], 'confirmed')
        self.assertEqual(self.act(created['id'], 'confirm').status_code, 409)
        self.assertEqual(self.create().status_code, 409)

    # AC-05
    def test_reschedule_records_previous_schedule_and_is_all_or_nothing(self):
        first = self.create(time='09:00').json()
        second = self.create(time='09:30').json()
        self.assertEqual(self.act(first['id'], 'reschedule', {'starts': at(FUTURE, '09:30')}).status_code, 400)
        clash = self.act(first['id'], 'reschedule', {'starts': at(FUTURE, '09:30'), 'reason': 'Pidió cambio'})
        self.assertEqual(clash.status_code, 409)
        self.assertEqual(Appointment.objects.get(pk=first['id']).starts.isoformat(), '2030-01-07T13:00:00+00:00')
        moved = self.act(first['id'], 'reschedule', {'starts': at(FUTURE, '09:15'), 'reason': 'x'})
        self.assertEqual(moved.status_code, 409)  # choca con la segunda
        self_move = self.act(second['id'], 'reschedule', {'starts': at(FUTURE, '09:45'),
                                                          'duration_minutes': 15, 'reason': ' Pidió cambio '})
        self.assertEqual(self_move.status_code, 200, self_move.content)
        event = self_move.json()['history'][-1]
        self.assertEqual((event['kind'], event['reason'], event['author_id']), ('rescheduled', 'Pidió cambio', self.admin.pk))
        self.assertEqual((event['previous_starts'], event['previous_ends']), (at(FUTURE, '09:30'), at(FUTURE, '10:00')))
        overlap_self = self.act(second['id'], 'reschedule', {'starts': at(FUTURE, '09:40'), 'reason': 'ajuste'})
        self.assertEqual(overlap_self.status_code, 200, overlap_self.content)  # excluye la propia

    # AC-06
    def test_cancel_requires_reason_frees_horario_and_stays_visible(self):
        created = self.create().json()
        self.assertEqual(self.act(created['id'], 'cancel', {'reason': '  '}).status_code, 400)
        cancelled = self.act(created['id'], 'cancel', {'reason': 'Paciente avisó'})
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()['status'], 'cancelled')
        self.assertEqual(cancelled.json()['allowed_actions'], [])
        self.assertEqual(self.create().status_code, 201)
        listed = self.client.get('/api/agenda/appointments/', {'status': 'cancelled'}).json()
        self.assertEqual(listed['count'], 1)
        self.assertEqual(self.act(created['id'], 'cancel', {'reason': 'otra'}).status_code, 409)

    # AC-07
    def test_attended_and_no_show_only_after_start(self):
        future = self.create().json()
        self.assertEqual(self.act(future['id'], 'attend').status_code, 409)
        self.assertEqual(self.act(future['id'], 'no-show').status_code, 409)
        past = self.create(day=PAST).json()
        self.assertIn('attend', past['allowed_actions'])
        attended = self.act(past['id'], 'attend')
        self.assertEqual((attended.status_code, attended.json()['status']), (200, 'attended'))
        no_show = self.create(day=PAST, time='09:30').json()
        self.assertEqual(self.act(no_show['id'], 'no-show').json()['status'], 'no_show')
        self.assertEqual(self.act(past['id'], 'no-show').status_code, 409)
        self.assertEqual(AppointmentEvent.objects.filter(kind='attended').count(), 1)

    # AC-08
    def test_list_filters_search_and_notes(self):
        created = self.create(notes='  Llegar temprano ').json()
        self.create(day=PAST)
        base = '/api/agenda/appointments/'
        self.assertEqual(self.client.get(base).json()['count'], 2)
        self.assertEqual(self.client.get(base, {'from': FUTURE, 'to': FUTURE}).json()['count'], 1)
        self.assertEqual(self.client.get(base, {'search': 'rosa'}).json()['count'], 2)
        self.assertEqual(self.client.get(base, {'search': 'zzz'}).json()['count'], 0)
        self.assertEqual(self.client.get(base, {'professional': str(self.pro.pk)}).json()['count'], 2)
        self.assertEqual(self.client.get(base, {'status': 'bogus'}).status_code, 400)
        detail = self.client.patch(f"{base}{created['id']}/", {'notes': 'Nueva nota'}, format='json')
        self.assertEqual(detail.json()['notes'], 'Nueva nota')

    def test_free_slots_exclude_pauses_and_occupied(self):
        self.create(time='09:00')
        response = self.client.get('/api/agenda/appointments/free-slots/', {
            'professional': str(self.pro.pk), 'date_from': FUTURE, 'date_to': FUTURE, 'duration': 30})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['slots'], [
            {'starts': at(FUTURE, '09:30'), 'ends': at(FUTURE, '10:00')},
            {'starts': at(FUTURE, '10:30'), 'ends': at(FUTURE, '12:00')},
        ])
