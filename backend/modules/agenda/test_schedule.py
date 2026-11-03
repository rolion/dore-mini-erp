from datetime import date, time
from types import SimpleNamespace
from unittest import TestCase

from modules.agenda.domain.schedule import shifts_overlap, subtract, validate_shift


class ScheduleTests(TestCase):
    def test_rejects_overnight_shift(self):
        self.assertIn('ends', validate_shift(
            0, time(22), time(2), date(2026, 11, 2), date(2026, 11, 8), []
        ))

    def test_overlap_requires_same_occurrence_and_noncontiguous_hours(self):
        first = SimpleNamespace(day=0, starts=time(9), ends=time(12),
                                valid_from=date(2026, 11, 2), valid_until=date(2026, 11, 8))
        second = SimpleNamespace(**vars(first))
        self.assertTrue(shifts_overlap(first, second))
        second.starts = time(12)
        second.ends = time(13)
        self.assertFalse(shifts_overlap(first, second))
        second.starts = time(10)
        second.valid_from = date(2026, 11, 3)
        self.assertFalse(shifts_overlap(first, second))

    def test_subtracts_union_of_pause_and_absence(self):
        result = list(subtract(time(9), time(12), [(time(10), time(10, 30)), (time(10, 15), time(11))]))
        self.assertEqual(result, [(time(9), time(10)), (time(11), time(12))])
