from datetime import datetime, timedelta, timezone
from unittest import TestCase

from modules.agenda.domain.appointment import (
    Appointment, AppointmentRuleError, InvalidTransition, clean_reason, fits_in, intervals_overlap,
)

T = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)
H = timedelta(minutes=30)


class AppointmentRuleTests(TestCase):
    def test_contiguous_intervals_do_not_overlap_but_partial_do(self):
        self.assertFalse(intervals_overlap(T, T + H, T + H, T + 2 * H))
        self.assertTrue(intervals_overlap(T, T + H, T + H / 2, T + H * 3 / 2))

    def test_must_fit_in_a_single_available_interval(self):
        available = [(T, T + H), (T + H * 2, T + H * 4)]
        self.assertTrue(fits_in(T, T + H, available))
        self.assertFalse(fits_in(T + H / 2, T + H * 3 / 2, available))
        self.assertFalse(fits_in(T, T + H * 4, available))

    def test_reason_is_required_trimmed_and_bounded(self):
        self.assertEqual(clean_reason('  paciente avisó '), 'paciente avisó')
        for bad in ('', '   ', None, 'x' * 501):
            with self.assertRaises(AppointmentRuleError):
                clean_reason(bad)

    def test_lifecycle(self):
        appointment = Appointment('scheduled', T, T + H)
        appointment.confirm()
        self.assertEqual(appointment.status, 'confirmed')
        with self.assertRaises(InvalidTransition):
            appointment.confirm()
        appointment.cancel()
        self.assertEqual(appointment.allowed_actions(T + H), [])
        for action in (appointment.cancel, lambda: appointment.reschedule(T, T + H)):
            with self.assertRaises(InvalidTransition):
                action()

    def test_attend_and_no_show_only_after_start(self):
        appointment = Appointment('confirmed', T, T + H)
        with self.assertRaises(InvalidTransition):
            appointment.mark_attended(T - timedelta(minutes=1))
        with self.assertRaises(InvalidTransition):
            appointment.mark_no_show(T - timedelta(minutes=1))
        appointment.mark_attended(T)
        self.assertEqual(appointment.status, 'attended')
        with self.assertRaises(InvalidTransition):
            appointment.mark_no_show(T + H)

    def test_reschedule_keeps_status_and_returns_previous(self):
        appointment = Appointment('confirmed', T, T + H)
        previous = appointment.reschedule(T + H, T + 2 * H)
        self.assertEqual(previous, (T, T + H))
        self.assertEqual((appointment.status, appointment.starts), ('confirmed', T + H))
        with self.assertRaises(AppointmentRuleError):
            appointment.reschedule(T, T)
