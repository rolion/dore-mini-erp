from datetime import date

from django.test import SimpleTestCase

from modules.reporting.domain.period import Period, PeriodError, PeriodKind, resolve_period

WEDNESDAY = date(2026, 10, 14)


class ResolvePeriodTests(SimpleTestCase):
    def resolve(self, kind=None, date_from=None, date_to=None, today=WEDNESDAY) -> Period:
        return resolve_period(kind, date_from, date_to, today)

    def test_day_is_today(self):  # AC-14
        self.assertEqual(self.resolve('day'), Period(PeriodKind.DAY, WEDNESDAY, WEDNESDAY))

    def test_week_runs_monday_to_sunday(self):  # AC-14, EDGE-11
        expected = Period(PeriodKind.WEEK, date(2026, 10, 12), date(2026, 10, 18))
        for today in (date(2026, 10, 12), WEDNESDAY, date(2026, 10, 18)):  # lunes, miércoles, domingo
            with self.subTest(today=today):
                self.assertEqual(self.resolve('week', today=today), expected)
        self.assertEqual(self.resolve('week', today=date(2026, 10, 19)).date_from, date(2026, 10, 19))

    def test_week_can_cross_a_month_and_year_boundary(self):  # EDGE-11
        self.assertEqual(self.resolve('week', today=date(2026, 12, 31)),
                         Period(PeriodKind.WEEK, date(2026, 12, 28), date(2027, 1, 3)))

    def test_month_is_first_to_last_day(self):  # AC-14, EDGE-11
        self.assertEqual(self.resolve('month'), Period(PeriodKind.MONTH, date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual(self.resolve('month', today=date(2028, 2, 10)).date_to, date(2028, 2, 29))  # bisiesto
        self.assertEqual(self.resolve('month', today=date(2026, 2, 10)).date_to, date(2026, 2, 28))
        self.assertEqual(self.resolve('month', today=date(2026, 12, 31)).date_to, date(2026, 12, 31))

    def test_defaults_to_the_current_month(self):  # AC-14
        self.assertEqual(self.resolve(), self.resolve('month'))

    def test_explicit_range_is_kept_as_is(self):  # AC-14, EDGE-02
        self.assertEqual(self.resolve(date_from=date(2026, 1, 1), date_to=date(2026, 3, 15)),
                         Period(PeriodKind.RANGE, date(2026, 1, 1), date(2026, 3, 15)))
        single = self.resolve(date_from=date(2026, 5, 5), date_to=date(2026, 5, 5))
        self.assertEqual((single.date_from, single.date_to), (date(2026, 5, 5), date(2026, 5, 5)))

    def test_rejects_period_together_with_dates(self):  # AC-14
        with self.assertRaises(PeriodError) as ctx:
            self.resolve('week', date_from=date(2026, 1, 1), date_to=date(2026, 1, 2))
        self.assertEqual(list(ctx.exception.errors), ['period'])

    def test_rejects_a_single_date(self):  # AC-14
        with self.assertRaises(PeriodError) as ctx:
            self.resolve(date_from=date(2026, 1, 1))
        self.assertEqual(list(ctx.exception.errors), ['date_to'])
        with self.assertRaises(PeriodError) as ctx:
            self.resolve(date_to=date(2026, 1, 1))
        self.assertEqual(list(ctx.exception.errors), ['date_from'])

    def test_rejects_an_inverted_range(self):  # AC-14
        with self.assertRaises(PeriodError) as ctx:
            self.resolve(date_from=date(2026, 2, 1), date_to=date(2026, 1, 1))
        self.assertEqual(list(ctx.exception.errors), ['date_to'])

    def test_rejects_unknown_kinds_including_range(self):  # AC-14
        for bad in ('year', 'range', 'hoy'):
            with self.subTest(kind=bad):
                with self.assertRaises(PeriodError) as ctx:
                    self.resolve(bad)
                self.assertEqual(list(ctx.exception.errors), ['period'])
