from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from types import SimpleNamespace
from unittest import TestCase

from modules.agenda.application.week import week_availability
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

    def test_rejects_invalid_breaks(self):
        args = (0, time(9), time(12), date(2026, 11, 2), date(2026, 11, 8))
        self.assertIn('breaks', validate_shift(*args, [(time(8), time(9, 30))]))
        self.assertIn('breaks', validate_shift(*args, [(time(10), time(10))]))
        self.assertIn('breaks', validate_shift(*args, [(time(10), time(11)), (time(10, 30), time(11, 30))]))
        self.assertEqual(validate_shift(*args, [(time(10), time(10, 30)), (time(10, 30), time(11))]), {})

    def test_vigencies_adjacent_do_not_overlap_but_coinciding_do(self):
        first = SimpleNamespace(day=0, starts=time(9), ends=time(12),
                                valid_from=date(2026, 11, 2), valid_until=date(2026, 11, 8))
        adjacent = SimpleNamespace(**{**vars(first), 'valid_from': date(2026, 11, 9), 'valid_until': date(2026, 11, 15)})
        coinciding = SimpleNamespace(**{**vars(first), 'valid_until': date(2026, 11, 2)})
        self.assertFalse(shifts_overlap(first, adjacent))
        self.assertTrue(shifts_overlap(first, coinciding))

    def test_week_availability_with_central_multiday_and_overlapping_absences(self):
        zone = ZoneInfo('America/La_Paz')
        shift = SimpleNamespace(day=0, starts=time(9), ends=time(12), breaks=[],
                                valid_from=date(2026, 11, 2), valid_until=date(2026, 11, 8))

        def absence(start, end):
            return SimpleNamespace(starts=datetime(*start, tzinfo=zone), ends=datetime(*end, tzinfo=zone))

        def hours(absences):
            _, availability = week_availability([shift], absences, date(2026, 11, 2), zone)
            return [(item['starts'][11:16], item['ends'][11:16]) for item in availability]

        self.assertEqual(hours([absence((2026, 11, 2, 10), (2026, 11, 2, 11))]), [('09:00', '10:00'), ('11:00', '12:00')])
        self.assertEqual(hours([absence((2026, 11, 1, 20), (2026, 11, 3, 8))]), [])
        self.assertEqual(hours([absence((2026, 11, 2, 9, 30), (2026, 11, 2, 10, 30)),
                                absence((2026, 11, 2, 10), (2026, 11, 2, 11))]), [('09:00', '09:30'), ('11:00', '12:00')])
