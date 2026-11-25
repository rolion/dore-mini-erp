"""API de tareas y actividad comercial (AC-01…AC-08) con dos empresas y PostgreSQL."""
from datetime import timedelta
from uuid import uuid4

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.crm.infrastructure.django.models import ActivityModel, OpportunityModel, TaskModel

from .test_api_opportunities import OpportunityApiBase

TASKS = '/api/crm/tasks/'
ACTIVITIES = '/api/crm/activities/'


def iso(delta: timedelta) -> str:
    return (timezone.now() + delta).isoformat()


class TaskApiBase(OpportunityApiBase):
    def setUp(self):
        super().setUp()
        self.buyer = self.customer('Cliente Uno', '76543210')

    def task(self, expected=201, **data):
        payload = {'title': 'Llamar', 'due_at': iso(timedelta(days=1)), 'customer_id': str(self.buyer.id), **data}
        response = self.client.post(TASKS, payload, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def act(self, task_id, action, data=None, expected=200):
        response = self.client.post(f'{TASKS}{task_id}/{action}/', data or {}, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def listing(self, **params):
        response = self.client.get(TASKS, params)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()


class CreateTaskTests(TaskApiBase):
    def test_create_for_customer_defaults_owner_to_actor(self):  # AC-01
        body = self.task(company_id=str(uuid4()))
        self.assertEqual(set(body), {'id', 'title', 'related', 'owner', 'due_at', 'status', 'is_overdue',
                                     'completed_at', 'created_at'})
        self.assertEqual((body['status'], body['owner']['id'], body['completed_at']), ('pending', self.user.id, None))
        self.assertEqual(body['related'], {'type': 'customer', 'id': str(self.buyer.id), 'name': 'Cliente Uno'})
        self.assertEqual(TaskModel.objects.get(pk=body['id']).company_id, self.company.id)

    def test_create_for_opportunity(self):  # AC-01
        opportunity = self.create(customer_id=str(self.buyer.id))
        body = self.task(customer_id=None, opportunity_id=opportunity['id'])
        self.assertEqual(body['related'], {'type': 'opportunity', 'id': opportunity['id'], 'name': 'Pack familiar'})

    def test_validation(self):  # AC-01, AC-02
        self.assertIn('customer_id', self.task(expected=400, customer_id=None))
        opportunity = self.create(customer_id=str(self.buyer.id))
        self.assertIn('customer_id', self.task(expected=400, opportunity_id=opportunity['id']))
        self.assertIn('title', self.task(expected=400, title='  '))
        self.assertIn('due_at', self.task(expected=400, due_at=None))
        other_user = make_admin(make_company('CRM B'), username='ajeno')
        self.assertIn('owner_id', self.task(expected=400, owner_id=other_user.id))

    def test_foreign_related_is_404(self):  # AC-02, AC-08
        other = make_company('CRM B')
        self.task(expected=404, customer_id=str(self.customer(company=other).id))
        self.task(expected=404, customer_id=None, opportunity_id=str(uuid4()))
        foreign = OpportunityModel.objects.create(
            company_id=other.id, board_id=self.board['id'], stage_id=self.stages[0], owner_id=1, title='x',
            amount=1, lead=self.lead(company=other))
        self.task(expected=404, customer_id=None, opportunity_id=str(foreign.id))

    def test_inactive_customer_and_closed_opportunity_conflict(self):  # AC-02, INV-07
        inactive = self.customer('Baja', active=False)
        self.assertEqual(self.task(expected=409, customer_id=str(inactive.id))['code'], 'customer_inactive')
        opportunity = self.create(customer_id=str(self.buyer.id))
        self.post(opportunity['id'], 'close', {'result': 'won'})
        self.assertEqual(self.task(expected=409, customer_id=None, opportunity_id=opportunity['id'])['code'],
                         'opportunity_closed')


class TransitionTests(TaskApiBase):
    def test_complete_sets_completed_at_and_cannot_repeat(self):  # AC-03
        task = self.task()
        done = self.act(task['id'], 'complete')
        self.assertEqual((done['status'], done['activity']), ('done', None))
        self.assertIsNotNone(done['completed_at'])
        self.assertEqual(self.act(task['id'], 'complete', expected=409)['code'], 'invalid_task_transition')

    def test_complete_with_activity_is_atomic(self):  # AC-03
        task = self.task()
        body = self.act(task['id'], 'complete', {'activity': {'channel': 'call', 'outcome': 'contacted',
                                                              'notes': 'Atendió'}})
        self.assertEqual(body['activity']['task_id'], task['id'])
        self.assertEqual(body['activity']['customer_id'], str(self.buyer.id))
        self.assertEqual(ActivityModel.objects.count(), 1)
        bad = self.task()
        self.act(bad['id'], 'complete', {'activity': {'channel': 'fax', 'notes': 'x'}}, expected=400)
        self.act(bad['id'], 'complete', {'activity': {'channel': 'call'}}, expected=400)
        self.assertEqual(TaskModel.objects.get(pk=bad['id']).status, 'pending')
        self.assertEqual(ActivityModel.objects.count(), 1)

    def test_complete_with_activity_rejected_for_inactive_customer(self):  # INV-07 (REV-01)
        customer = self.customer('Baja', '76000000')
        task = self.task(customer_id=str(customer.id))
        customer.active = False
        customer.save()
        body = self.act(task['id'], 'complete', {'activity': {'channel': 'call', 'notes': 'x'}}, expected=409)
        self.assertEqual(body['code'], 'customer_inactive')
        self.assertEqual(TaskModel.objects.get(pk=task['id']).status, 'pending')
        self.assertEqual(ActivityModel.objects.count(), 0)
        self.assertEqual(self.act(task['id'], 'complete')['status'], 'done')  # sin actividad sí se completa

    def test_cancel_reopen_archive(self):  # AC-04
        task = self.task()
        self.assertEqual(self.act(task['id'], 'cancel')['status'], 'cancelled')
        self.assertEqual(self.act(task['id'], 'reopen')['status'], 'pending')
        self.act(task['id'], 'archive', expected=409)  # una pendiente no se archiva
        self.act(task['id'], 'complete')
        reopened = self.act(task['id'], 'reopen')
        self.assertEqual((reopened['status'], reopened['completed_at']), ('pending', None))
        self.act(task['id'], 'cancel')
        self.assertEqual(self.act(task['id'], 'archive')['status'], 'archived')
        for action in ('cancel', 'reopen', 'archive', 'complete'):
            self.act(task['id'], action, expected=409)

    def test_archived_hidden_from_every_list(self):  # AC-04, INV-08
        task = self.task()
        self.act(task['id'], 'cancel')
        self.act(task['id'], 'archive')
        for status in ('all', 'pending', 'done', 'cancelled', 'overdue'):
            self.assertEqual(self.listing(status=status)['count'], 0, status)
        self.assertEqual(self.listing()['count'], 0)

    def test_edit_only_pending(self):  # AC-06
        task = self.task()
        edited = self.client.patch(f"{TASKS}{task['id']}/", {'title': 'Visitar', 'owner_id': self.user.id},
                                   format='json')
        self.assertEqual((edited.status_code, edited.json()['title']), (200, 'Visitar'))
        self.assertEqual(self.client.patch(f"{TASKS}{task['id']}/", {'title': ' '}, format='json').status_code, 400)
        foreign_owner = make_admin(make_company('CRM C'), username='otro').id
        response = self.client.patch(f"{TASKS}{task['id']}/", {'owner_id': foreign_owner}, format='json')
        self.assertEqual((response.status_code, 'owner_id' in response.json()), (400, True))
        self.client.patch(f"{TASKS}{task['id']}/", {'customer_id': str(uuid4())}, format='json')
        self.assertEqual(self.client.get(f"{TASKS}{task['id']}/").json()['related']['id'], str(self.buyer.id))
        self.act(task['id'], 'complete')
        response = self.client.patch(f"{TASKS}{task['id']}/", {'title': 'Otro'}, format='json')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'task_not_pending'))


class ListTaskTests(TaskApiBase):
    def test_filters_order_and_overdue(self):  # AC-05
        late = self.task(title='Vencida', due_at=iso(timedelta(days=-2)))
        soon = self.task(title='Mañana', due_at=iso(timedelta(days=1)))
        done = self.task(title='Hecha', due_at=iso(timedelta(days=-1)))
        self.act(done['id'], 'complete')
        cancelled = self.task(title='Cancelada')
        self.act(cancelled['id'], 'cancel')
        titles = lambda **p: [t['title'] for t in self.listing(**p)['results']]  # noqa: E731
        self.assertEqual(titles(), ['Vencida', 'Hecha', 'Mañana', 'Cancelada'])  # por vencimiento ascendente
        self.assertEqual(titles(status='pending'), ['Vencida', 'Mañana'])
        self.assertEqual(titles(status='overdue'), ['Vencida'])
        self.assertEqual(titles(status='done'), ['Hecha'])
        self.assertEqual(titles(status='cancelled'), ['Cancelada'])
        self.assertEqual(titles(status='all'), titles())
        flags = {t['title']: t['is_overdue'] for t in self.listing()['results']}
        self.assertEqual(flags, {'Vencida': True, 'Mañana': False, 'Hecha': False, 'Cancelada': False})
        self.assertEqual(late['is_overdue'], True)
        self.assertEqual(soon['is_overdue'], False)
        self.assertEqual(self.client.get(TASKS, {'status': 'archived'}).status_code, 400)

    def test_listing_uses_a_constant_number_of_queries(self):  # AC-05 (REV-03)
        def queries() -> int:
            with CaptureQueriesContext(connection) as captured:
                self.assertEqual(self.client.get(TASKS).status_code, 200)
            return len(captured)

        self.task(title='Primera')
        opportunity = self.create(customer_id=str(self.buyer.id))
        self.task(title='De oportunidad', customer_id=None, opportunity_id=opportunity['id'])
        few = queries()
        for number in range(6):
            self.task(title=f'Otra {number}', customer_id=str(self.customer(f'C{number}').id))
        self.assertEqual(queries(), few)

    def test_filter_by_owner_and_related(self):  # AC-05
        mate = make_admin(self.company, username='colega')
        self.task(title='Mía')
        self.task(title='Del colega', owner_id=mate.id)
        opportunity = self.create(customer_id=str(self.buyer.id))
        self.task(title='De la oportunidad', customer_id=None, opportunity_id=opportunity['id'])
        self.assertEqual([t['title'] for t in self.listing(owner_id=mate.id)['results']], ['Del colega'])
        self.assertEqual(self.listing(owner_id=mate.id)['results'][0]['owner']['name'].split(' (')[1], 'colega)')
        self.assertEqual(self.listing(customer_id=self.buyer.id)['count'], 2)
        self.assertEqual([t['title'] for t in self.listing(opportunity_id=opportunity['id'])['results']],
                         ['De la oportunidad'])
        self.assertEqual(self.client.get(TASKS, {'owner_id': 'x'}).status_code, 400)

    def test_pagination(self):  # AC-05
        for number in range(3):
            self.task(title=f'T{number}', due_at=iso(timedelta(days=number + 1)))
        page = self.client.get(TASKS, {'page_size': 2}).json()
        self.assertEqual((page['count'], len(page['results'])), (3, 2))


class IsolationTests(TaskApiBase):
    def test_other_company_cannot_see_or_touch(self):  # AC-08
        task = self.task()
        activity = self.client.post(ACTIVITIES, {'customer_id': str(self.buyer.id), 'channel': 'call',
                                                 'notes': 'x'}, format='json').json()
        other_user = make_admin(make_company('CRM B'), username='ajeno')
        authenticate(self.client, other_user)
        self.assertEqual(self.listing()['count'], 0)
        self.assertEqual(self.client.get(f"{TASKS}{task['id']}/").status_code, 404)
        self.assertEqual(self.client.patch(f"{TASKS}{task['id']}/", {'title': 'x'}, format='json').status_code, 404)
        for action in ('complete', 'cancel', 'reopen', 'archive'):
            self.act(task['id'], action, expected=404)
        self.assertEqual(self.client.get(ACTIVITIES, {'customer_id': str(self.buyer.id)}).status_code, 404)
        self.assertEqual(ActivityModel.objects.filter(pk=activity['id']).count(), 1)
        self.assertEqual(TaskModel.objects.get(pk=task['id']).status, 'pending')

    def test_requires_login_and_customers_module(self):  # AC-08
        self.disable('customers')
        self.assertEqual(self.client.get(TASKS).status_code, 403)
        self.assertEqual(self.client.get(ACTIVITIES, {'customer_id': str(self.buyer.id)}).status_code, 403)
        self.client.credentials()
        self.assertIn(self.client.get(TASKS).status_code, (401, 403))


class ActivityApiTests(TaskApiBase):
    def record(self, expected=201, **data):
        payload = {'customer_id': str(self.buyer.id), 'channel': 'whatsapp', 'outcome': 'interested',
                   'notes': 'Pidió precios', **data}
        response = self.client.post(ACTIVITIES, payload, format='json')
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def test_create_persists_and_lists_most_recent_first(self):  # AC-07
        old = self.record(occurred_at=iso(timedelta(days=-3)), notes='Antigua')
        new = self.record(notes='Nueva')
        self.assertEqual((new['actor']['id'], new['channel'], new['task_id']), (self.user.id, 'whatsapp', None))
        stored = ActivityModel.objects.get(pk=old['id'])
        self.assertEqual((stored.company_id, stored.customer_id), (self.company.id, self.buyer.id))
        listed = self.client.get(ACTIVITIES, {'customer_id': str(self.buyer.id)}).json()
        self.assertEqual([a['notes'] for a in listed['results']], ['Nueva', 'Antigua'])

    def test_on_opportunity_even_if_closed(self):  # AC-07, INV-07
        opportunity = self.create(customer_id=str(self.buyer.id))
        self.post(opportunity['id'], 'close', {'result': 'won'})
        body = self.record(customer_id=None, opportunity_id=opportunity['id'])
        self.assertEqual(body['opportunity_id'], opportunity['id'])
        listed = self.client.get(ACTIVITIES, {'opportunity_id': opportunity['id']}).json()
        self.assertEqual(listed['count'], 1)

    def test_validation(self):  # AC-07
        self.assertIn('notes', self.record(expected=400, outcome='', notes=''))
        self.assertIn('channel', self.record(expected=400, channel='sms'))
        self.assertIn('outcome', self.record(expected=400, outcome='great'))
        self.assertIn('occurred_at', self.record(expected=400, occurred_at=iso(timedelta(days=2))))
        self.assertIn('customer_id', self.record(expected=400, customer_id=None))
        self.assertEqual(self.record(outcome='', notes='Solo nota')['outcome'], '')

    def test_list_requires_one_entity_and_inactive_customer_rejected(self):  # AC-07
        self.assertEqual(self.client.get(ACTIVITIES).status_code, 400)
        inactive = self.customer('Baja', active=False)
        self.assertEqual(self.record(expected=409, customer_id=str(inactive.id))['code'], 'customer_inactive')

    def test_immutable(self):  # AC-07
        activity = self.record()
        url = f"{ACTIVITIES}{activity['id']}/"
        for method in (self.client.patch, self.client.put, self.client.delete):
            self.assertIn(method(url, {}, format='json').status_code, (404, 405))
