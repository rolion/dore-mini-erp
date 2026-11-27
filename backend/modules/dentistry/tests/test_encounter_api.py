from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone as dt_timezone
from threading import Barrier
from unittest.mock import patch
from zoneinfo import ZoneInfo
from uuid import uuid4

from django.db import close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.agenda.models import Appointment
from modules.customers.infrastructure.django.models import CustomerModel
from modules.dentistry.infrastructure.encounter_models import EncounterModel
from modules.dentistry.infrastructure.evaluation_models import EvaluationModel
from modules.personnel.infrastructure.django.models import ProfessionalModel

ROOT = '/api/dentistry/'
APPOINTMENTS = ROOT + 'appointments/'
AGENDA = '/api/agenda/appointments/'


def enable(client, *keys):
    for key in keys or ('dentistry', 'personnel', 'agenda', 'services'):
        response = client.post(f'/api/modules/{key}/enable/', {}, format='json')
        assert response.status_code == 200, (key, response.content)


class Base:
    def prepare(self):
        self.company = make_company()
        self.user = make_admin(self.company)
        authenticate(self.client, self.user)
        enable(self.client)
        self.professional = ProfessionalModel.objects.create(
            company_id=self.company.id, name='Dra. Rojas', created_by=self.user.pk, updated_by=self.user.pk)
        self.customer = self.patient('Ana')
        self.other_customer = CustomerModel.objects.create(
            company_id=self.company.id, name='Carlos', phone='+59170000001')

    def patient(self, name):
        customer = CustomerModel.objects.create(company_id=self.company.id, name=name, phone='+59176543210')
        response = self.client.post(ROOT + 'patients/', {'customer_id': str(customer.id), 'allergies': 'Penicilina'},
                                    format='json')
        assert response.status_code == 201, response.content
        return customer

    def appointment(self, customer=None, *, status='confirmed', hours_ago=1.0, company_id=None):
        customer = customer or self.customer
        starts = timezone.now() - timedelta(hours=hours_ago)
        return Appointment.objects.create(
            company_id=company_id or self.company.id, professional_id=self.professional.id, customer_id=customer.id,
            customer_name=customer.name, service_id=uuid4(), service_name='Limpieza', starts=starts,
            ends=starts + timedelta(minutes=30), duration_minutes=30, status=status, created_by=self.user.pk)

    @staticmethod
    def url(appointment, action=''):
        return f'{APPOINTMENTS}{appointment.id}/encounter/{action}'

    def start(self, appointment):
        response = self.client.post(self.url(appointment, 'start/'))
        self.assertIn(response.status_code, (200, 201), response.content)
        return response.json()

    def odontogram(self, encounter_id, **extra):
        return self.client.post(f'{ROOT}encounters/{encounter_id}/odontogram/', self.draft_body(**extra),
                                format='json')

    def draft_body(self, **extra):
        data = {'dentition': 'permanent', 'findings': [{'piece': 16, 'condition': 'caries', 'surfaces': ['O']}]}
        data.update(extra)
        return data


class EncounterApiTests(Base, APITestCase):
    def setUp(self):
        self.prepare()

    def test_list_shows_only_dental_appointments_with_filters(self):  # AC-01
        first, second = self.appointment(hours_ago=2), self.appointment(hours_ago=1)
        self.appointment(self.other_customer)  # sin perfil odontológico: no aparece
        self.start(first)
        data = self.client.get(APPOINTMENTS).json()
        self.assertEqual(data['count'], 2)
        self.assertEqual([r['appointment_id'] for r in data['results']], [str(first.id), str(second.id)])
        self.assertEqual([r['encounter_status'] for r in data['results']], ['in_progress', 'pending'])
        self.assertEqual(data['results'][0]['professional_name'], 'Dra. Rojas')
        self.assertEqual(self.client.get(APPOINTMENTS, {'encounter_status': 'pending'}).json()['count'], 1)
        self.assertEqual(self.client.get(APPOINTMENTS, {'encounter_status': 'in_progress'}).json()['count'], 1)
        self.assertEqual(self.client.get(APPOINTMENTS, {'search': 'zzz'}).json()['count'], 0)
        self.assertEqual(self.client.get(APPOINTMENTS, {'status': 'cancelled'}).json()['count'], 0)
        self.assertEqual(self.client.get(APPOINTMENTS, {'professional': str(uuid4())}).json()['count'], 0)
        yesterday = (timezone.localdate() - timedelta(days=3)).isoformat()
        self.assertEqual(self.client.get(APPOINTMENTS, {'from': yesterday, 'to': yesterday}).json()['count'], 0)
        self.assertEqual(self.client.get(APPOINTMENTS, {'from': '2026-01-01', 'to': '2026-12-31'}).status_code, 400)

    def test_times_are_returned_in_the_agenda_time_zone(self):
        appointment = self.appointment()
        listed = self.client.get(APPOINTMENTS).json()['results'][0]
        detail = self.client.get(self.url(appointment)).json()['appointment']
        agenda = self.client.get(f'{AGENDA}{appointment.id}/').json()
        self.assertEqual((listed['starts'], detail['starts']), (agenda['starts'], agenda['starts']))
        self.assertTrue(agenda['starts'].endswith('-04:00'), agenda['starts'])
        started = self.start(appointment)['encounter']['started_at']
        self.assertTrue(started.endswith('-04:00'), started)

    def test_detail_shows_patient_summary_and_actions(self):  # AC-01
        appointment = self.appointment()
        data = self.client.get(self.url(appointment)).json()
        self.assertEqual((data['appointment']['customer_name'], data['appointment']['professional_name']),
                         ('Ana', 'Dra. Rojas'))
        self.assertEqual((data['allowed_actions'], data['encounter'], data['is_dental']), (['start'], None, True))
        self.assertEqual(data['patient']['allergies'], 'Penicilina')
        self.assertFalse(data['prescriptions_enabled'])  # AC-11

    def test_start_and_finish_without_odontogram_or_prescriptions(self):  # AC-02, AC-10
        appointment = self.appointment()
        response = self.client.post(self.url(appointment, 'start/'))
        self.assertEqual(response.status_code, 201, response.content)
        encounter = response.json()['encounter']
        self.assertEqual((encounter['status'], encounter['started_by']['id']), ('in_progress', self.user.id))
        self.assertEqual(response.json()['allowed_actions'], ['finish', 'cancel'])
        done = self.client.post(self.url(appointment, 'finish/'))
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual((done.json()['encounter']['status'], done.json()['appointment']['status']),
                         ('finished', 'attended'))
        self.assertIsNotNone(done.json()['encounter']['finished_at'])
        self.assertEqual(done.json()['allowed_actions'], [])
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'attended')

    def test_start_and_finish_are_idempotent(self):  # AC-04
        appointment = self.appointment()
        first = self.start(appointment)['encounter']['id']
        again = self.client.post(self.url(appointment, 'start/'))
        self.assertEqual((again.status_code, again.json()['encounter']['id']), (200, first))
        self.assertEqual(EncounterModel.objects.count(), 1)
        self.client.post(self.url(appointment, 'finish/'))
        repeat = self.client.post(self.url(appointment, 'finish/'))
        self.assertEqual((repeat.status_code, repeat.json()['encounter']['status']), (200, 'finished'))
        self.assertEqual(appointment.events.filter(kind='attended').count(), 1)
        self.assertEqual(self.client.post(self.url(appointment, 'start/')).status_code, 409)

    def test_failed_close_rolls_back_both_states(self):  # AC-04
        appointment = self.appointment()
        self.start(appointment)
        self.client.raise_request_exception = False
        with patch('modules.dentistry.infrastructure.encounter_repository.DjangoEncounterRepository.save',
                   side_effect=RuntimeError('boom')):
            self.assertEqual(self.client.post(self.url(appointment, 'finish/')).status_code, 500)
        appointment.refresh_from_db()
        self.assertEqual((appointment.status, EncounterModel.objects.get().status), ('confirmed', 'in_progress'))

    def test_finish_with_draft_odontogram_is_blocked_until_confirmed(self):  # AC-09
        appointment = self.appointment()
        encounter_id = self.start(appointment)['encounter']['id']
        self.client.post(f'{ROOT}encounters/{encounter_id}/odontogram/', self.draft_body(), format='json')
        blocked = self.client.post(self.url(appointment, 'finish/'))
        self.assertEqual((blocked.status_code, blocked.json()['code']), (409, 'draft_pending'))
        appointment.refresh_from_db()
        self.assertEqual((appointment.status, EncounterModel.objects.get().status), ('confirmed', 'in_progress'))
        evaluation = EvaluationModel.objects.get()
        self.client.post(f'{ROOT}evaluations/{evaluation.id}/confirm/')
        self.assertEqual(self.client.post(self.url(appointment, 'finish/')).status_code, 200)

    def test_cancel_requires_reason_and_cancels_both(self):  # AC-05
        appointment = self.appointment()
        encounter_id = self.start(appointment)['encounter']['id']
        self.client.post(f'{ROOT}encounters/{encounter_id}/odontogram/', self.draft_body(), format='json')
        for body in ({}, {'reason': ''}, {'reason': '  '}, {'reason': 'x' * 501}):
            self.assertEqual(self.client.post(self.url(appointment, 'cancel/'), body, format='json').status_code, 400)
        done = self.client.post(self.url(appointment, 'cancel/'), {'reason': 'Paciente con fiebre'}, format='json')
        self.assertEqual(done.status_code, 200, done.content)
        encounter = done.json()['encounter']
        self.assertEqual((encounter['status'], encounter['cancellation_reason']), ('cancelled', 'Paciente con fiebre'))
        self.assertEqual(encounter['cancelled_by']['id'], self.user.id)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'cancelled')
        self.assertEqual(appointment.events.filter(kind='cancelled').get().reason, 'Paciente con fiebre')
        self.assertEqual(EvaluationModel.objects.count(), 1)  # los datos clínicos se conservan
        self.assertEqual(self.client.post(self.url(appointment, 'finish/')).status_code, 409)

    def test_cannot_start_ineligible_appointments(self):  # AC-05, INV-07
        for status in ('cancelled', 'no_show', 'attended'):
            response = self.client.post(self.url(self.appointment(status=status), 'start/'))
            self.assertEqual((response.status_code, response.json()['code']), (409, 'not_eligible'), status)
        future = self.client.post(self.url(self.appointment(hours_ago=-2), 'start/'))
        self.assertEqual((future.status_code, future.json()['code']), (409, 'too_early'))
        other = self.client.post(self.url(self.appointment(self.other_customer), 'start/'))
        self.assertEqual((other.status_code, other.json()['code']), (409, 'not_dental'))
        self.assertEqual(EncounterModel.objects.count(), 0)  # no se crea atención innecesaria

    def test_reschedule_before_start_keeps_history_then_blocked(self):  # AC-05, INV-08, INV-09
        appointment = self.appointment(hours_ago=-3)
        detail = self.client.get(self.url(appointment)).json()
        self.assertEqual(detail['allowed_actions'], [])
        past = self.appointment(hours_ago=1)
        self.start(past)
        for action, body in (('reschedule', {'starts': '2030-01-01T09:00:00', 'reason': 'x'}),
                             ('cancel', {'reason': 'x'}), ('no-show', {})):
            response = self.client.post(f'{AGENDA}{past.id}/{action}/', body, format='json')
            self.assertEqual((response.status_code, response.json()['code']), (409, 'encounter_started'), action)

    def test_agenda_blocks_attend_for_dental_but_not_for_other_appointments(self):  # AC-08
        dental, other = self.appointment(), self.appointment(self.other_customer)
        blocked = self.client.post(f'{AGENDA}{dental.id}/attend/')
        self.assertEqual((blocked.status_code, blocked.json()['code']), (409, 'clinical_flow_required'))
        self.assertEqual(self.client.post(f'{AGENDA}{other.id}/attend/').status_code, 200)
        self.start(dental)
        again = self.client.post(f'{AGENDA}{dental.id}/attend/')
        self.assertEqual(again.json()['code'], 'clinical_flow_required')
        dental.refresh_from_db()
        self.assertEqual(dental.status, 'confirmed')

    def test_agenda_attend_allowed_when_dentistry_disabled(self):  # AC-08
        dental = self.appointment()
        self.client.post('/api/modules/dentistry/disable/')
        self.assertEqual(self.client.post(f'{AGENDA}{dental.id}/attend/').status_code, 200)

    def test_odontogram_from_encounter_preloads_context_and_is_unique(self):  # AC-03
        appointment = self.appointment()
        missing = self.client.post(f'{ROOT}encounters/{uuid4()}/odontogram/', {}, format='json')
        self.assertEqual(missing.status_code, 404)
        encounter_id = self.start(appointment)['encounter']['id']
        created = self.odontogram(encounter_id)
        self.assertEqual(created.status_code, 201, created.content)
        data = created.json()
        self.assertEqual((data['encounter_id'], data['professional']['id'], data['status']),
                         (encounter_id, str(self.professional.id), 'draft'))
        la_paz_today = timezone.now().astimezone(ZoneInfo('America/La_Paz')).date()
        self.assertEqual(data['clinical_date'], la_paz_today.isoformat())
        second = self.client.post(f'{ROOT}encounters/{encounter_id}/odontogram/', self.draft_body(), format='json')
        self.assertEqual((second.status_code, second.json()['code']), (409, 'odontogram_exists'))
        detail = self.client.get(self.url(appointment)).json()['odontogram']
        self.assertEqual((detail['root']['id'], detail['can_create']), (data['id'], False))

    def test_amendment_keeps_original_and_encounter(self):  # AC-03
        appointment = self.appointment()
        encounter_id = self.start(appointment)['encounter']['id']
        draft = self.odontogram(encounter_id).json()
        self.client.post(f'{ROOT}evaluations/{draft["id"]}/confirm/')
        amended = self.client.post(f'{ROOT}evaluations/{draft["id"]}/amend/', {'reason': 'Corrección'}, format='json')
        self.assertEqual(amended.status_code, 201, amended.content)
        self.assertEqual(amended.json()['encounter_id'], encounter_id)
        original = EvaluationModel.objects.get(pk=draft['id'])
        self.assertEqual((original.status, original.encounter_id and str(original.encounter_id)),
                         ('confirmed', encounter_id))
        data = self.client.get(self.url(appointment)).json()['odontogram']
        self.assertEqual((data['root']['id'], data['current']['id'], data['versions']),
                         (draft['id'], amended.json()['id'], 2))

    def test_odontogram_requires_encounter_in_progress(self):  # INV-06
        appointment = self.appointment()
        encounter_id = self.start(appointment)['encounter']['id']
        self.client.post(self.url(appointment, 'finish/'))
        response = self.client.post(f'{ROOT}encounters/{encounter_id}/odontogram/', self.draft_body(), format='json')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'encounter_finished'))

    def test_observations_while_in_progress_only(self):
        appointment = self.appointment()
        encounter_id = self.start(appointment)['encounter']['id']
        saved = self.client.patch(f'{ROOT}encounters/{encounter_id}/', {'observations': 'Sensibilidad'}, format='json')
        self.assertEqual(saved.json()['encounter']['observations'], 'Sensibilidad')
        self.assertEqual(self.client.patch(f'{ROOT}encounters/{encounter_id}/', {'observations': 'x' * 2001},
                                           format='json').status_code, 400)
        self.client.post(self.url(appointment, 'finish/'))
        self.assertEqual(self.client.patch(f'{ROOT}encounters/{encounter_id}/', {'observations': 'z'},
                                           format='json').status_code, 409)

    def test_two_appointments_give_independent_encounters_in_history(self):  # AC-06
        first, second = self.appointment(hours_ago=3), self.appointment(hours_ago=1)
        first_id, second_id = self.start(first)['encounter']['id'], self.start(second)['encounter']['id']
        self.assertNotEqual(first_id, second_id)
        self.client.post(self.url(first, 'finish/'))
        history = self.client.get(f'{ROOT}patients/{self.customer.id}/encounters/').json()
        self.assertEqual(history['count'], 2)
        self.assertEqual({item['status'] for item in history['results']}, {'finished', 'in_progress'})
        self.assertEqual(self.client.get(f'{ROOT}patients/{uuid4()}/encounters/').status_code, 404)

    def test_company_isolation_and_clinical_policy(self):  # AC-07
        appointment = self.appointment()
        encounter_id = self.start(appointment)['encounter']['id']
        other = make_admin(make_company('Otra'), username='otra')
        other_client = APIClient()
        authenticate(other_client, other)
        enable(other_client)
        self.assertEqual(other_client.get(self.url(appointment)).status_code, 404)
        self.assertEqual(other_client.post(self.url(appointment, 'start/')).status_code, 404)
        self.assertEqual(other_client.post(self.url(appointment, 'finish/')).status_code, 404)
        self.assertEqual(other_client.patch(f'{ROOT}encounters/{encounter_id}/', {'observations': 'x'},
                                            format='json').status_code, 404)
        self.assertEqual(other_client.post(f'{ROOT}encounters/{encounter_id}/odontogram/', {}, format='json')
                         .status_code, 404)
        self.assertEqual(other_client.get(APPOINTMENTS).json()['count'], 0)
        foreign = self.appointment(company_id=other.company_id)
        self.assertEqual(self.client.get(self.url(foreign)).status_code, 404)
        self.user.role = 'reception'
        self.user.save()
        for url in (APPOINTMENTS, self.url(appointment), f'{ROOT}patients/{self.customer.id}/encounters/'):
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(self.url(appointment, 'finish/')).status_code, 403)

    def test_module_disabled_blocks_endpoints(self):  # AC-07
        appointment = self.appointment()
        self.client.post('/api/modules/agenda/disable/')
        self.assertEqual(self.client.get(self.url(appointment)).json()['code'], 'module_disabled')

    def test_odontogram_cannot_attach_to_other_patient_data(self):  # AC-07
        appointment = self.appointment()
        encounter_id = self.start(appointment)['encounter']['id']
        body = self.draft_body(customer_id=str(self.other_customer.id), professional_id=str(uuid4()))
        created = self.client.post(f'{ROOT}encounters/{encounter_id}/odontogram/', body, format='json').json()
        self.assertEqual(created['customer_id'], str(self.customer.id))
        self.assertEqual(created['professional']['id'], str(self.professional.id))

    def test_odontogram_clinical_date_uses_the_agenda_time_zone(self):  # REV-08
        appointment = self.appointment()
        encounter_id = self.start(appointment)['encounter']['id']
        day = timezone.localdate() - timedelta(days=1)
        # 01:30 UTC del día siguiente = 21:30 del día `day` en La Paz (UTC-4)
        started = datetime.combine(day + timedelta(days=1), datetime.min.time(), dt_timezone.utc)
        EncounterModel.objects.filter(pk=encounter_id).update(started_at=started + timedelta(minutes=90))
        self.assertEqual(self.odontogram(encounter_id).json()['clinical_date'], day.isoformat())

    def test_odontogram_for_archived_patient_has_its_own_code(self):  # REV-01
        appointment = self.appointment()
        encounter_id = self.start(appointment)['encounter']['id']
        self.client.post(f'{ROOT}patients/{self.customer.id}/archive/')
        response = self.odontogram(encounter_id)
        self.assertEqual((response.status_code, response.json()['code']), (409, 'patient_archived'))

    def test_listing_filters_by_customer_and_state_within_the_range(self):  # REV-03
        mine, other = self.appointment(hours_ago=2), self.appointment(self.patient('Beatriz'), hours_ago=1)
        self.start(other)
        only = self.client.get(APPOINTMENTS, {'customer': str(self.customer.id)}).json()
        self.assertEqual([r['appointment_id'] for r in only['results']], [str(mine.id)])
        done = self.client.get(APPOINTMENTS, {'encounter_status': 'in_progress'}).json()
        self.assertEqual([r['appointment_id'] for r in done['results']], [str(other.id)])
        page = self.client.get(APPOINTMENTS, {'page': 2, 'page_size': 1}).json()
        self.assertEqual((page['count'], len(page['results'])), (2, 1))

    def test_legacy_evaluations_have_no_encounter(self):  # AC-12
        response = self.client.post(f'{ROOT}patients/{self.customer.id}/evaluations/', {
            'dentition': 'permanent', 'clinical_date': timezone.localdate().isoformat(),
            'findings': [{'piece': 16, 'condition': 'caries', 'surfaces': ['O']}]}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(response.json()['encounter_id'])
        self.assertIsNone(EvaluationModel.objects.get().encounter_id)
        appointment = self.appointment()
        encounter_id = self.start(appointment)['encounter']['id']
        blocked = self.client.post(f'{ROOT}encounters/{encounter_id}/odontogram/', self.draft_body(), format='json')
        self.assertEqual((blocked.status_code, blocked.json()['code']), (409, 'draft_exists'))


class EncounterConcurrencyTests(Base, TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.prepare()

    def parallel(self, call, workers=2):
        barrier = Barrier(workers)

        def worker(_):
            close_old_connections()
            client = APIClient()
            authenticate(client, self.user)
            barrier.wait()
            try:
                return call(client)
            finally:
                close_old_connections()
        with ThreadPoolExecutor(workers) as pool:
            return list(pool.map(worker, range(workers)))

    def test_simultaneous_start_creates_one_encounter(self):  # AC-04
        appointment = self.appointment()
        responses = self.parallel(lambda c: c.post(self.url(appointment, 'start/')))
        self.assertEqual(sorted(r.status_code for r in responses), [200, 201])
        self.assertEqual(EncounterModel.objects.count(), 1)

    def test_simultaneous_odontogram_creation_creates_one(self):  # AC-03
        appointment = self.appointment()
        encounter_id = self.start(appointment)['encounter']['id']
        responses = self.parallel(lambda c: c.post(
            f'{ROOT}encounters/{encounter_id}/odontogram/', self.draft_body(), format='json'))
        self.assertEqual(sorted(r.status_code for r in responses), [201, 409])
        self.assertEqual(EvaluationModel.objects.filter(encounter_id=encounter_id).count(), 1)

    def test_simultaneous_finish_and_amend_do_not_break(self):  # REV-04
        appointment = self.appointment()
        encounter_id = self.start(appointment)['encounter']['id']
        draft = self.odontogram(encounter_id).json()
        self.client.post(f'{ROOT}evaluations/{draft["id"]}/confirm/')
        calls = [lambda c: c.post(self.url(appointment, 'finish/')),
                 lambda c: c.post(f'{ROOT}evaluations/{draft["id"]}/amend/', {'reason': 'x'}, format='json')]
        barrier, results = Barrier(2), []

        def worker(call):
            close_old_connections()
            client = APIClient()
            authenticate(client, self.user)
            barrier.wait()
            try:
                results.append(call(client).status_code)
            finally:
                close_old_connections()
        with ThreadPoolExecutor(2) as pool:
            list(pool.map(worker, calls))
        self.assertTrue(all(code in (200, 201, 409) for code in results), results)
        finished = EncounterModel.objects.get().status == 'finished'
        drafts = EvaluationModel.objects.filter(encounter_id=encounter_id, status='draft').count()
        if not finished:  # finalizar perdió: había un borrador pendiente
            self.assertEqual(drafts, 1)

    def test_simultaneous_finish_is_consistent(self):  # AC-04
        appointment = self.appointment()
        self.start(appointment)
        responses = self.parallel(lambda c: c.post(self.url(appointment, 'finish/')))
        self.assertEqual([r.status_code for r in responses], [200, 200])
        self.assertEqual(appointment.events.filter(kind='attended').count(), 1)
