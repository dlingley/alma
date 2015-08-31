from datetime import datetime, timedelta
from unittest.mock import patch

from django.forms import ValidationError
from django.test import TestCase
from django.utils.timezone import now
from model_mommy.mommy import make, prepare

from alma.items.models import Item
from alma.loans.models import Loan
from alma.users.models import User
from alma.utils.tests import AlmaTest

from .enums import DayOfWeek
from .forms import OmniForm, RequestDeleteForm
from .models import Request, Reservation, iter_intervals


class DayOfWeekTest(TestCase):
    def test(self):
        self.assertEqual(int(DayOfWeek(33)), 33)
        self.assertEqual(str(DayOfWeek(33)), "Sun, Fri")
        self.assertEqual(list(DayOfWeek(33)), [DayOfWeek.SUNDAY, DayOfWeek.FRIDAY])
        self.assertEqual(int(DayOfWeek.from_list([DayOfWeek.FRIDAY, DayOfWeek.MONDAY])), DayOfWeek.FRIDAY | DayOfWeek.MONDAY)


class IterIntervalsTest(TestCase):
    def test_iter_intervals(self):
        duration = timedelta(hours=1)
        start = now()
        # Jan 4 2015 is a Sunday
        start = start.replace(year=2015, month=1, day=4)

        # test no repeating
        end = start+duration
        end_repeating_on = start+timedelta(days=20)
        intervals = list(iter_intervals(start, end, end_repeating_on=end_repeating_on))
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0].start, start)
        self.assertEqual(intervals[0].end, start+duration)

        # test repeating on Monday and Wednesday, but the end ends before we hit Wednesday
        end_repeating_on = start+timedelta(days=2)
        intervals = list(iter_intervals(start, end, end_repeating_on=end_repeating_on, repeat_on=DayOfWeek.MONDAY | DayOfWeek.WEDNESDAY))
        self.assertEqual(len(intervals), 2)
        self.assertEqual(intervals[0].start, start)
        self.assertEqual(intervals[0].end, start+duration)
        self.assertEqual(intervals[1].start, start+timedelta(days=1))
        self.assertEqual(intervals[1].end, start+timedelta(days=1)+duration)

        # test repeating on Monday and Wednesday
        end_repeating_on = start+timedelta(days=14)
        intervals = list(iter_intervals(start, end, end_repeating_on=end_repeating_on, repeat_on=DayOfWeek.MONDAY | DayOfWeek.WEDNESDAY))
        self.assertEqual(len(intervals), 5)
        self.assertEqual(intervals[-1].start, start+timedelta(days=10))
        self.assertEqual(intervals[-1].end, start+timedelta(days=10)+duration)

        # test that the end date is included (i.e. the <= operator is used to compare the dates)
        end_repeating_on = start+timedelta(days=3)
        intervals = list(iter_intervals(start, end, end_repeating_on, repeat_on=DayOfWeek.MONDAY | DayOfWeek.WEDNESDAY))
        self.assertEqual(len(intervals), 3)


class RequestTest(AlmaTest):
    def test_cache_key(self):
        res = prepare(Reservation)
        res.save(starting_on=now(), ending_on=now()+timedelta(hours=1))
        r1 = prepare(Request, pk=1, reservation=res)
        r2 = prepare(Request, pk=2, reservation=res)
        self.assertNotEqual(r1.cache_key, r2.cache_key)

    def test_intersects(self):
        start_0 = now()
        end_0 = now()+timedelta(minutes=1)

        # equal dates should obviously intersect
        # [---0---]
        # [---1---]
        start_1 = start_0
        end_1 = end_0
        self.assertTrue(Request(start=start_0, end=end_0).intersects(Request(start=start_1, end=end_1)))

        # if they touch edges, that is not considered an intersection
        #  [---0---]
        #          [---1---]
        start_1 = end_0
        end_1 = end_0+timedelta(minutes=1)
        self.assertFalse(Request(start=start_0, end=end_0).intersects(Request(start=start_1, end=end_1)))
        # if they touch edges, that is not considered an intersection
        #          [---0---]
        #  [---1---]
        start_1 = start_0 - timedelta(minutes=1)
        end_1 = start_0
        self.assertFalse(Request(start=start_0, end=end_0).intersects(Request(start=start_1, end=end_1)))
        #        [---0---]
        #  [---1---]
        start_1 = start_0 - timedelta(minutes=1)
        end_1 = start_0+timedelta(seconds=90)
        self.assertTrue(Request(start=start_0, end=end_0).intersects(Request(start=start_1, end=end_1)))
        #  [---0---]
        #      [---1---]
        start_1 = start_0 + timedelta(seconds=30)
        end_1 = start_1+timedelta(minutes=2)
        self.assertTrue(Request(start=start_0, end=end_0).intersects(Request(start=start_1, end=end_1)))
        #  [---0---]
        #    [-1-]
        start_1 = start_0 + timedelta(seconds=30)
        end_1 = start_1+timedelta(seconds=1)
        self.assertTrue(Request(start=start_0, end=end_0).intersects(Request(start=start_1, end=end_1)))

    def test_to_html(self):
        res = prepare(Reservation, repeat_on=DayOfWeek.MONDAY | DayOfWeek.TUESDAY)
        res.save(starting_on=now(), ending_on=now()+timedelta(hours=1))
        r = make(Request, reservation=res)
        html = r.to_html()
        self.assertIn("Mon, Tue", html)


class OmniFormTest(AlmaTest):
    def test_clean_user(self):
        """
        Ensure only ODIN usernames are accepted, and that users are created on the fly
        """
        form = OmniForm()
        form.cleaned_data = {'user': "_asdf"}
        self.assertRaises(ValidationError, form.clean_user)
        form.cleaned_data = {'user': "matt (mdj2)"}
        with patch("alma.requests.forms.is_ldap_user", return_value=True):
            form.clean_user()
        self.assertTrue(User.objects.filter(email="mdj2@pdx.edu").exists())
        self.assertFalse(User.objects.get(email="mdj2@pdx.edu").is_active)

    def test_clean_end_repeating_on(self):
        form = OmniForm()
        form.cleaned_data = {'end_repeating_on': datetime(year=2012, month=12, day=12, hour=12, minute=12, second=12)}
        self.assertEqual(form.clean_end_repeating_on(), datetime(year=2012, month=12, day=12, hour=23, minute=59, second=59))

    def test_clean_repeat_on(self):
        form = OmniForm()
        form.cleaned_data = {'repeat_on': [DayOfWeek.SUNDAY, DayOfWeek.TUESDAY]}
        self.assertEqual(form.clean_repeat_on(), DayOfWeek.SUNDAY | DayOfWeek.TUESDAY)
        # when the repeat_on field isn't filled out, it should be set to zero
        form = OmniForm()
        form.cleaned_data = {'repeat_on': None}
        self.assertEqual(form.clean_repeat_on(), 0)

    def test_clean(self):
        # if repeat is on, then the repeat_on and end_repeating_on fields are required
        form = OmniForm({"repeat": True})
        form.is_valid()
        self.assertIn("repeat_on", form._errors)
        self.assertIn("end_repeating_on", form._errors)
        # if repeat is off, then those fields should be set to their defaults
        form = OmniForm({
            "repeat": False,
            "repeat_on": [DayOfWeek.MONDAY],
            "end_repeating_on": datetime(year=2012, month=12, day=12, hour=23, minute=59, second=59)
        })
        form.is_valid()
        self.assertEqual(form.cleaned_data["repeat_on"], 0)
        self.assertEqual(form.cleaned_data["end_repeating_on"], None)

        # ensure the start date is > the end date
        form = OmniForm({
            "repeat": False,
            "starting_on": datetime(year=2012, month=12, day=12),
            "ending_on": datetime(year=2012, month=12, day=12),
        })
        form.is_valid()
        self.assertIn("This needs to be less than the ending on date", str(form.errors))

        # ensure the starting_on *date* is > end_repeating_on date
        form = OmniForm({
            "repeat": True,
            "starting_on": datetime(year=2012, month=12, day=12),
            "end_repeating_on": datetime(year=2012, month=12, day=11),
        })
        form.is_valid()
        self.assertIn("The end repeating on date must be greater than the starting on date", str(form.errors))

        # if there are no errors on the form, the availability should be checked
        # item = make(Item)
        # data = {
        #     "item": "foo (%s)" % (item.pk),
        #     "user": "Matt (mdj2)",
        #     "starting_on": datetime(year=2012, month=12, day=12),
        #     "ending_on": datetime(year=2012, month=12, day=13),
        # }
        # with patch("alma.requests.forms.Request.objects.is_available", return_value=True):
        #     with patch("alma.requests.forms.is_ldap_user", return_value=True):
        #         form = OmniForm(data)
        #         self.assertTrue(form.is_valid())

        # with patch("alma.requests.forms.Request.objects.is_available", return_value=False):
        #     with patch("alma.requests.forms.is_ldap_user", return_value=True):
        #         form = OmniForm(data)
        #         self.assertFalse(form.is_valid())

    def test_reservation_and_requests_are_created_on_save(self):
        dt = now()
        dt = dt.replace(year=2015, month=1, day=5, hour=10, minute=10, second=10)
        item = make(Item)
        cleaned_data = {
            "bibs_or_item": [item.bib],
            "user": make(User),
            "repeat_on": DayOfWeek.MONDAY | DayOfWeek.FRIDAY,
            "starting_on": dt,
            "ending_on": dt + timedelta(hours=1),
            "end_repeating_on": dt + timedelta(days=30),
        }
        created_by = make(User)
        form = OmniForm()
        form.cleaned_data = cleaned_data

        form.save(created_by=created_by)

        self.assertEqual(Reservation.objects.count(), 1)
        reservation = Reservation.objects.first()
        self.assertEqual(reservation.created_by, created_by)
        self.assertEqual(reservation.user, cleaned_data['user'])
        self.assertEqual(reservation.bib, cleaned_data['bibs_or_item'][0])
        # 9 Request objects should be tied to this reservation
        self.assertEqual(Request.objects.filter(reservation=reservation).count(), 9)

    def test_loan_is_created_on_save(self):
        item = make(Item)
        cleaned_data = {
            "bibs_or_item": item,
            "user": make(User),
        }
        created_by = make(User)
        form = OmniForm()
        form.cleaned_data = cleaned_data

        form.save(created_by=created_by)
        self.assertEqual(Loan.objects.count(), 1)
        loan = Loan.objects.first()
        self.assertEqual(loan.user, cleaned_data['user'])
        self.assertEqual(loan.item, cleaned_data['bibs_or_item'])

    def test_loan_is_returned_on_save(self):
        item = make(Item)
        user = make(User)
        # create a loan that can be returned
        loan = make(Loan, user=user, item=item, returned_on=None)
        cleaned_data = {
            "bibs_or_item": item,
            "user": user,
        }
        created_by = make(User)
        form = OmniForm()
        form.cleaned_data = cleaned_data

        form.save(created_by=created_by)
        self.assertEqual(Loan.objects.count(), 1)
        loan = Loan.objects.first()
        self.assertEqual(loan.user, cleaned_data['user'])
        self.assertEqual(loan.item, cleaned_data['bibs_or_item'])
        self.assertNotEqual(loan.returned_on, None)


class RequestDeleteFormTest(AlmaTest):
    def test_extra_choices_for_repeating_reservations_become_choices(self):
        res = prepare(Reservation, repeat_on=0)
        res.save(starting_on=now(), ending_on=now()+timedelta(hours=1))
        r = make(Request, reservation=res)
        form = RequestDeleteForm(request=r)
        self.assertNotIn("This and all after it", str(form['choice']))
        self.assertNotIn("The entire series", str(form['choice']))

        # now make the reservation repeat, and now we should see the extra choices
        res = prepare(Reservation, repeat_on=DayOfWeek.MONDAY | DayOfWeek.TUESDAY)
        res.save(starting_on=now(), ending_on=now()+timedelta(hours=1))
        r = make(Request, reservation=res)
        form = RequestDeleteForm(request=r)
        self.assertIn("This and all after it", str(form['choice']))
        self.assertIn("The entire series", str(form['choice']))

    def test_save_when_deleting_just_the_single_request(self):
        res = prepare(Reservation, repeat_on=DayOfWeek.MONDAY | DayOfWeek.TUESDAY)
        res.save(starting_on=now(), ending_on=now()+timedelta(hours=1), end_repeating_on=now()+timedelta(days=14))
        request = Request.objects.filter(reservation=res).order_by("pk").first()
        pre_count = Request.objects.count()

        form = RequestDeleteForm({"delete": 1, "choice": RequestDeleteForm.THIS}, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(pre_count-1, Request.objects.count())

    def test_save_when_deleting_entire_series(self):
        res = prepare(Reservation, repeat_on=DayOfWeek.MONDAY | DayOfWeek.TUESDAY)
        res.save(starting_on=now(), ending_on=now()+timedelta(hours=1), end_repeating_on=now()+timedelta(days=14))
        request = Request.objects.filter(reservation=res).order_by("pk").last()

        form = RequestDeleteForm({"delete": 1, "choice": RequestDeleteForm.THE_ENTIRE_SERIES}, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(0, Request.objects.count())

    def test_save_when_this_and_all_after_is_chosen(self):
        res = prepare(Reservation, repeat_on=DayOfWeek.MONDAY | DayOfWeek.TUESDAY)
        res.save(starting_on=now(), ending_on=now()+timedelta(hours=1), end_repeating_on=now()+timedelta(days=14))
        # since we're getting the second Request in the reservation, all but
        # the first should be deleted
        request = list(Request.objects.filter(reservation=res).order_by("pk"))[1]

        form = RequestDeleteForm({"delete": 1, "choice": RequestDeleteForm.THIS_AND_ALL_AFTER}, request=request)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(1, Request.objects.count())
