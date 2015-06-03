"""
The limitation with the Alma software is that it doesn't allow repeating
bookings/requests for an item. The whole point of *this* application is to get
around that. A Request here can have one or more days (RequestInterval)
associated with it. Thus, allowing for repeating reservations.
"""
from django.db import models
from datetime import timedelta
from django.template.loader import render_to_string
from alma.alma.api import create_booking, delete_booking
from .enums import DayOfWeek


#class RequestManager(models.Manager):
#    def is_available(self, bib, start, end, repeat_on=0, end_repeating_on=None):
#        request = Request(repeat_on=repeat_on)
#        duration = end - start
#        if end_repeating_on is None:
#            end_repeating_on = end
#
#        intervals = list(RequestInterval.objects.filter(
#            Q(start__lte=end_repeating_on)|Q(end__lte=end_repeating_on)
#        ).filter(
#            Q(start__gte=start)|Q(end__gte=start)
#        ).filter(
#            request__bib__pk=bib.pk
#        ).order_by("start"))
#
#        # the best we can do here is O(n*lg(n)) (I think)
#        intervals.extend(request.iter_intervals(start, end_repeating_on, duration))
#        intervals.sort(key=lambda interval: (interval.start, interval.end))
#        for index, interval in enumerate(intervals[:-1]):
#            if interval.intersects(intervals[index+1]):
#                return False
#        return True

def iter_intervals(starting_on, ending_on, end_repeating_on=None, repeat_on=0):
    """
    Yields two-tuples containing aware datetimes representing an interval.
    """
    start = starting_on
    end = end_repeating_on or ending_on
    duration = ending_on - start

    date = start
    while date <= end:
        if date == start or ((2**((date.weekday()+1) % 7)) & repeat_on):
            yield (date, date+duration)
        date += timedelta(days=1)


class Reservation(models.Model):
    """
    A Reservation object reserves a particular Bib for a particular user during
    a set of time intervals represented by Request objects.
    """
    reservation_id = models.AutoField(primary_key=True)
    # an enum value bitwise or-ing DayOfWeek
    repeat_on = models.IntegerField(default=0)

    created_on = models.DateTimeField(auto_now_add=True)
    edited_on = models.DateTimeField(auto_now=True)

    # the person who created the Request within the app
    created_by = models.ForeignKey("users.User", null=True, on_delete=models.SET_NULL, related_name="+")
    # the person who is actually requesting the item
    user = models.ForeignKey("users.User")
    # the bib being requested
    bib = models.ForeignKey("items.Bib")

    class Meta:
        db_table = "reservation"

    def first_request(self):
        """Get the first Request object associated with this reservation"""
        return Request.objects.filter(reservation_id=self.pk).order_by("start").first()

    def last_request(self):
        """Get the last Request object associated with this reservation"""
        return Request.objects.filter(reservation_id=self.pk).order_by("-end").first()

    def save(self, *args, starting_on, ending_on, end_repeating_on=None, **kwargs):
        """
        Saves the reservation, and all the related Requests
        """
        to_return = super().save(*args, **kwargs)
        for interval in iter_intervals(starting_on, ending_on, end_repeating_on, self.repeat_on):
            Request(start=interval[0], end=interval[1], reservation=self).save()

        return to_return

    def delete(self, *args, **kwargs):
        """
        Deletes all the related Requests and then this reservation itself
        """
        requests = Request.objects.filter(reservation=self)
        for request in requests:
            request.delete()
        super().delete(*args, **kwargs)


class Request(models.Model):
    """
    Represents a Request in Alma. This object must have a parent Reservation
    object, which ties one or more Request objects together (which is necessary
    to support repeating reservations)
    """
    # this is the actual Request ID from Alma
    request_id = models.CharField(primary_key=True, max_length=255)
    start = models.DateTimeField(help_text="Starting datetime of the request")
    end = models.DateTimeField(help_text="Ending datetime of the request")

    reservation = models.ForeignKey(Reservation, help_text="The parent reservation linking one or more requests together")
    loan = models.OneToOneField("loans.Loan", null=True, default=None)

    class Meta:
        db_table = "request"

    @property
    def cache_key(self):
        # any mutable field that appears in the popover should be used to
        # create the cache key
        return "|".join(map(str, [self.pk]))

    def intersects(self, other):
        return self.start < other.end and self.end > other.start

    def save(self, *args, **kwargs):
        if not self.request_id:
            response = create_booking(username=self.reservation.user.username, mms_id=self.reservation.bib.mms_id, start_date=self.start, end_date=self.end)
            self.pk = response['request_id']
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        response = delete_booking(self.request_id, self.reservation.bib.mms_id)
        super().delete(*args, **kwargs)

    def to_html(self):
        days = ""
        if self.reservation.repeat_on:
            days = str(DayOfWeek(self.reservation.repeat_on))

        form = RequestChangeForm(requests=[self])
        return render_to_string("requests/_popover.html", {
            "form": form,
            "request": self,
            "days": days,
        })


from .forms import RequestChangeForm
