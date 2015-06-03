from datetime import timedelta, datetime
from model_mommy.mommy import make, prepare
from unittest.mock import Mock, patch
from elasticmodels import ESTestCase
from django.test import TestCase
from django.utils.timezone import now
from django.forms import ValidationError
from alma.users.models import User
from alma.items.models import Item
from .enums import DayOfWeek
from .models import Request, RequestInterval
from .forms import RequestForm


class DayOfWeekTest(TestCase):
    def test(self):
        self.assertEqual(int(DayOfWeek(33)), 33)
        self.assertEqual(str(DayOfWeek(33)), "Sun, Fri")
        self.assertEqual(list(DayOfWeek(33)), [DayOfWeek.SUNDAY, DayOfWeek.FRIDAY])
        self.assertEqual(int(DayOfWeek.from_list([DayOfWeek.FRIDAY, DayOfWeek.MONDAY])), DayOfWeek.FRIDAY | DayOfWeek.MONDAY)


class RequestTest(TestCase):
    def test_iter_intervals(self):
        duration = timedelta(hours=1)
        start = now()
        # Jan 4 2015 is a Sunday
        start = start.replace(year=2015, month=1, day=4)

        # test no repeating
        end = start+timedelta(days=20)
        request = prepare(Request, repeat_on=0)
        intervals = list(request.iter_intervals(start, end, duration))
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0].start, start)
        self.assertEqual(intervals[0].end, start+duration)

        # test repeating on Monday and Wednesday, but the end ends before we hit Wednesday
        end = start+timedelta(days=2)
        request = prepare(Request, repeat_on=DayOfWeek.MONDAY | DayOfWeek.WEDNESDAY)
        intervals = list(request.iter_intervals(start, end, duration))
        self.assertEqual(len(intervals), 2)
        self.assertEqual(intervals[0].start, start)
        self.assertEqual(intervals[0].end, start+duration)
        self.assertEqual(intervals[1].start, start+timedelta(days=1))
        self.assertEqual(intervals[1].end, start+timedelta(days=1)+duration)

        # test repeating on Monday and Wednesday
        end = start+timedelta(days=14)
        request = prepare(Request, repeat_on=DayOfWeek.MONDAY | DayOfWeek.WEDNESDAY)
        intervals = list(request.iter_intervals(start, end, duration))
        self.assertEqual(len(intervals), 5)
        self.assertEqual(intervals[-1].start, start+timedelta(days=10))
        self.assertEqual(intervals[-1].end, start+timedelta(days=10)+duration)

        # test that the end date is included (i.e. the <= operator is used to compare the dates)
        end = start+timedelta(days=3)
        request = prepare(Request, repeat_on=DayOfWeek.MONDAY | DayOfWeek.WEDNESDAY)
        intervals = list(request.iter_intervals(start, end, duration))
        self.assertEqual(len(intervals), 3)


class RequestIntervalTest(TestCase, ESTestCase):
    def test_cache_key(self):
        ri = prepare(RequestInterval, pk=1)
        ri2 = prepare(RequestInterval, pk=2)
        self.assertNotEqual(ri.cache_key, ri2.cache_key)

    def test_intersects(self):
        start_0 = now()
        end_0 = now()+timedelta(minutes=1)

        # equal dates should obviously intersect
        # [---0---]
        # [---1---]
        start_1 = start_0
        end_1 = end_0
        self.assertTrue(RequestInterval(start=start_0, end=end_0).intersects(RequestInterval(start=start_1, end=end_1)))

        # if they touch edges, that is not considered an intersection
        #  [---0---]
        #          [---1---]
        start_1 = end_0
        end_1 = end_0+timedelta(minutes=1)
        self.assertFalse(RequestInterval(start=start_0, end=end_0).intersects(RequestInterval(start=start_1, end=end_1)))
        # if they touch edges, that is not considered an intersection
        #          [---0---]
        #  [---1---]
        start_1 = start_0 - timedelta(minutes=1)
        end_1 = start_0
        self.assertFalse(RequestInterval(start=start_0, end=end_0).intersects(RequestInterval(start=start_1, end=end_1)))
        #        [---0---]
        #  [---1---]
        start_1 = start_0 - timedelta(minutes=1)
        end_1 = start_0+timedelta(seconds=90)
        self.assertTrue(RequestInterval(start=start_0, end=end_0).intersects(RequestInterval(start=start_1, end=end_1)))
        #  [---0---]
        #      [---1---]
        start_1 = start_0 + timedelta(seconds=30)
        end_1 = start_1+timedelta(minutes=2)
        self.assertTrue(RequestInterval(start=start_0, end=end_0).intersects(RequestInterval(start=start_1, end=end_1)))
        #  [---0---]
        #    [-1-]
        start_1 = start_0 + timedelta(seconds=30)
        end_1 = start_1+timedelta(seconds=1)
        self.assertTrue(RequestInterval(start=start_0, end=end_0).intersects(RequestInterval(start=start_1, end=end_1)))

    def test_to_html(self):
        ri = make(RequestInterval, request__repeat_on=DayOfWeek.MONDAY|DayOfWeek.TUESDAY)
        html = ri.to_html()
        self.assertIn("Mon, Tue", html)


class RequestFormTest(TestCase):
    def test_clean_user(self):
        """
        Ensure only ODIN usernames are accepted, and that users are created on the fly
        """
        form = RequestForm()
        form.cleaned_data = {'user': "_asdf"}
        self.assertRaises(ValidationError, form.clean_user)
        form.cleaned_data = {'user': "matt (mdj2)"}
        with patch("alma.requests.forms.is_ldap_user", return_value=True):
            form.clean_user()
        self.assertTrue(User.objects.filter(email="mdj2@pdx.edu").exists())
        self.assertFalse(User.objects.get(email="mdj2@pdx.edu").is_active)

    def test_clean_end_repeating_on(self):
        form = RequestForm()
        form.cleaned_data = {'end_repeating_on': datetime(year=2012, month=12, day=12, hour=12, minute=12, second=12)}
        self.assertEqual(form.clean_end_repeating_on(), datetime(year=2012, month=12, day=12, hour=23, minute=59, second=59))

    def test_clean_repeat_on(self):
        form = RequestForm()
        form.cleaned_data = {'repeat_on': [DayOfWeek.SUNDAY, DayOfWeek.TUESDAY]}
        self.assertEqual(form.clean_repeat_on(), DayOfWeek.SUNDAY | DayOfWeek.TUESDAY)
        # when the repeat_on field isn't filled out, it should be set to zero
        form = RequestForm()
        form.cleaned_data = {'repeat_on': None}
        self.assertEqual(form.clean_repeat_on(), 0)

    def test_clean(self):
        # if repeat is on, then the repeat_on and end_repeating_on fields are required
        form = RequestForm({"repeat": True})
        form.is_valid()
        self.assertIn("repeat_on", form._errors)
        self.assertIn("end_repeating_on", form._errors)
        # if repeat is off, then those fields should be set to their defaults
        form = RequestForm({
            "repeat": False,
            "repeat_on": [DayOfWeek.MONDAY],
            "end_repeating_on": datetime(year=2012, month=12, day=12, hour=23, minute=59, second=59)
        })
        form.is_valid()
        self.assertEqual(form.cleaned_data["repeat_on"], 0)
        self.assertEqual(form.cleaned_data["end_repeating_on"], None)

        # ensure the start date is > the end date
        form = RequestForm({
            "repeat": False,
            "starting_on": datetime(year=2012, month=12, day=12),
            "ending_on": datetime(year=2012, month=12, day=12),
        })
        form.is_valid()
        self.assertIn("This needs to be less than the ending on date", str(form.errors))

        # ensure the starting_on *date* is > end_repeating_on date
        form = RequestForm({
            "repeat": True,
            "starting_on": datetime(year=2012, month=12, day=12),
            "end_repeating_on": datetime(year=2012, month=12, day=11),
        })
        form.is_valid()
        self.assertIn("The end repeating on date must be greater than the starting on date", str(form.errors))

        # if there are no errors on the form, the availability should be checked
        item = make(Item)
        data = {
            "item": "foo (%s)" % (item.pk) ,
            "user": "Matt (mdj2)",
            "starting_on": datetime(year=2012, month=12, day=12),
            "ending_on": datetime(year=2012, month=12, day=13),
        }
        with patch("alma.requests.forms.Request.objects.is_available", return_value=True):
            with patch("alma.requests.forms.is_ldap_user", return_value=True):
                form = RequestForm(data)
                self.assertTrue(form.is_valid())

        with patch("alma.requests.forms.Request.objects.is_available", return_value=False):
            with patch("alma.requests.forms.is_ldap_user", return_value=True):
                form = RequestForm(data)
                self.assertFalse(form.is_valid())

    def test_save(self):
        dt = now()
        dt = dt.replace(year=2015, month=1, day=5, hour=10, minute=10, second=10)
        item = make(Item)
        form = RequestForm(data={
            "starting_on": dt,
            "ending_on": dt+timedelta(hours=2),
            "end_repeating_on": dt+timedelta(days=7),
            "user": 'foo (mdj2)',
            "item": 'foo (%s)' % item.pk,
            "repeat_on": [DayOfWeek.MONDAY, DayOfWeek.FRIDAY],
            "repeat": 1,
        })
        created_by = make(User)

        with patch("alma.requests.forms.is_ldap_user", return_value=True):
            request = form.save(created_by=created_by)
        self.assertEqual(request.created_by, created_by)
        self.assertEqual(RequestInterval.objects.count(), 3)
