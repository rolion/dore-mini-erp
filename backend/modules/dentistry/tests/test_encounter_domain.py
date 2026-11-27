from datetime import datetime, timezone
from unittest import TestCase
from uuid import uuid4

from modules.dentistry.domain.encounter import (
    CANCELLED, FINISHED, IN_PROGRESS, Encounter, EncounterStateError, EncounterValidationError,
)

NOW = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)


def encounter(**extra):
    return Encounter(uuid4(), uuid4(), uuid4(), started_at=NOW, **extra)


class EncounterDomainTests(TestCase):
    def test_new_encounter_is_in_progress_with_actions(self):  # INV-03
        item = encounter()
        self.assertEqual((item.status, item.allowed_actions()), (IN_PROGRESS, ['finish', 'cancel']))

    def test_finish_is_idempotent(self):  # INV-03, AC-04
        item = encounter()
        self.assertTrue(item.finish(NOW))
        self.assertFalse(item.finish(NOW))
        self.assertEqual((item.status, item.allowed_actions()), (FINISHED, []))

    def test_cancelled_cannot_finish_and_finished_cannot_cancel(self):  # INV-03
        cancelled = encounter()
        cancelled.cancel('  Paciente se retiró ', NOW)
        self.assertEqual((cancelled.status, cancelled.cancellation_reason), (CANCELLED, 'Paciente se retiró'))
        with self.assertRaises(EncounterStateError):
            cancelled.finish(NOW)
        finished = encounter()
        finished.finish(NOW)
        with self.assertRaises(EncounterStateError) as raised:
            finished.cancel('x', NOW)
        self.assertEqual(raised.exception.code, 'encounter_finished')

    def test_cancel_requires_reason_up_to_500(self):  # INV-05
        for reason in (None, '', '   ', 'x' * 501):
            item = encounter()
            with self.assertRaises(EncounterValidationError):
                item.cancel(reason, NOW)
            self.assertEqual(item.status, IN_PROGRESS)

    def test_observations_only_while_in_progress_and_bounded(self):
        item = encounter()
        item.set_observations('  Sensibilidad  ')
        self.assertEqual(item.observations, 'Sensibilidad')
        with self.assertRaises(EncounterValidationError):
            item.set_observations('x' * 2001)
        item.finish(NOW)
        with self.assertRaises(EncounterStateError):
            item.set_observations('otra')
