"""Dominio de tareas y actividades (AC-01, AC-04, AC-06, AC-07; INV-02…INV-06): puro, sin base de datos."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from django.test import SimpleTestCase

from modules.crm.domain.activity import NOTES_MAX, Activity
from modules.crm.domain.errors import CrmConflict, CrmValidationError
from modules.crm.domain.task import ARCHIVED, CANCELLED, DONE, PENDING, Task

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)


def make_task(**overrides) -> Task:
    values = {'customer_id': uuid4(), 'opportunity_id': None, 'title': ' Llamar ', 'due_at': NOW, 'owner_id': 1}
    return Task.create(**{**values, **overrides})


class TaskTests(SimpleTestCase):
    def test_create_cleans_title_and_starts_pending(self):
        task = make_task()
        self.assertEqual((task.title, task.status, task.completed_at), ('Llamar', PENDING, None))

    def test_requires_exactly_one_related(self):
        for related in ({'customer_id': None}, {'opportunity_id': uuid4()}):
            with self.assertRaises(CrmValidationError) as ctx:
                make_task(**related)
            self.assertIn('customer_id', ctx.exception.errors)

    def test_requires_title_and_due_at(self):
        with self.assertRaises(CrmValidationError) as ctx:
            make_task(title='  ', due_at=None)
        self.assertEqual(set(ctx.exception.errors), {'title', 'due_at'})
        with self.assertRaises(CrmValidationError):
            make_task(title='x' * 151)

    def test_complete_sets_completed_at_and_only_once(self):
        task = make_task()
        task.complete(NOW)
        self.assertEqual((task.status, task.completed_at), (DONE, NOW))
        with self.assertRaises(CrmConflict):
            task.complete(NOW)

    def test_transitions(self):
        task = make_task()
        task.cancel()
        self.assertEqual(task.status, CANCELLED)
        task.reopen()
        self.assertEqual((task.status, task.completed_at), (PENDING, None))
        task.complete(NOW)
        task.reopen()
        self.assertEqual((task.status, task.completed_at), (PENDING, None))
        task.cancel()
        task.archive()
        self.assertEqual(task.status, ARCHIVED)

    def test_invalid_transitions(self):
        task = make_task()
        for action in (task.reopen, task.archive):  # una pendiente no se reabre ni se archiva
            with self.assertRaises(CrmConflict):
                action()
        task.cancel()
        task.archive()
        for action in (task.cancel, task.reopen, task.archive, lambda: task.complete(NOW)):
            with self.assertRaises(CrmConflict):
                action()

    def test_edit_only_pending(self):
        task = make_task()
        task.edit(title='Visitar', due_at=NOW + timedelta(days=1), owner_id=2)
        self.assertEqual((task.title, task.owner_id), ('Visitar', 2))
        task.complete(NOW)
        with self.assertRaises(CrmConflict) as ctx:
            task.edit(title='Otro')
        self.assertEqual(ctx.exception.code, 'task_not_pending')

    def test_overdue_is_computed_for_pending_only(self):
        task = make_task(due_at=NOW - timedelta(minutes=1))
        self.assertTrue(task.is_overdue(NOW))
        task.complete(NOW)
        self.assertFalse(task.is_overdue(NOW))
        self.assertFalse(make_task(due_at=NOW + timedelta(minutes=1)).is_overdue(NOW))


def make_activity(**overrides) -> Activity:
    values = {'actor_id': 1, 'customer_id': uuid4(), 'opportunity_id': None, 'channel': 'call',
              'outcome': 'contacted', 'notes': ' Atendió ', 'occurred_at': None, 'now': NOW}
    return Activity.create(**{**values, **overrides})


class ActivityTests(SimpleTestCase):
    def test_create_defaults_to_now_and_trims_notes(self):
        activity = make_activity()
        self.assertEqual((activity.occurred_at, activity.notes), (NOW, 'Atendió'))

    def test_outcome_or_notes_required(self):
        with self.assertRaises(CrmValidationError):
            make_activity(outcome='', notes=' ')
        self.assertEqual(make_activity(outcome='', notes='Solo nota').outcome, '')
        self.assertEqual(make_activity(outcome='no_answer', notes='').outcome, 'no_answer')

    def test_validates_channel_outcome_and_length(self):
        with self.assertRaises(CrmValidationError) as ctx:
            make_activity(channel='sms', outcome='x', notes='y' * (NOTES_MAX + 1))
        self.assertEqual(set(ctx.exception.errors), {'channel', 'outcome', 'notes'})

    def test_future_date_rejected(self):
        with self.assertRaises(CrmValidationError) as ctx:
            make_activity(occurred_at=NOW + timedelta(minutes=1))
        self.assertIn('occurred_at', ctx.exception.errors)

    def test_requires_exactly_one_related(self):
        with self.assertRaises(CrmValidationError):
            make_activity(customer_id=None)
        with self.assertRaises(CrmValidationError):
            make_activity(opportunity_id=uuid4())
