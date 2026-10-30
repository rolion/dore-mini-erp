from datetime import datetime, timedelta, timezone as tz

from django.test import SimpleTestCase
from django.utils import timezone

from shared.test_runner import strictly_increasing


class StrictlyIncreasingClockTests(SimpleTestCase):
    def test_never_repeats_or_goes_back_even_if_the_real_clock_stalls(self):
        frozen = datetime(2026, 1, 1, tzinfo=tz.utc)
        now = strictly_increasing(lambda: frozen)
        values = [now() for _ in range(1000)]
        self.assertEqual(values, sorted(set(values)))
        self.assertEqual(values[1] - values[0], timedelta(microseconds=1))

    def test_follows_the_real_clock_when_it_moves_ahead(self):
        ticks = iter([datetime(2026, 1, 1, tzinfo=tz.utc), datetime(2026, 1, 2, tzinfo=tz.utc)])
        now = strictly_increasing(lambda: next(ticks))
        self.assertEqual((now(), now()), (datetime(2026, 1, 1, tzinfo=tz.utc), datetime(2026, 1, 2, tzinfo=tz.utc)))

    def test_the_runner_installs_it_for_django(self):
        self.assertNotEqual(timezone.now(), timezone.now())
