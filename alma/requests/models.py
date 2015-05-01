"""
The limitation with the Alma software is that it doesn't allow repeating
bookings/requests for an item. The whole point of *this* application is to get
around that. A Request here can have one or more days (RequestInterval)
associated with it. Thus, allowing for repeating reservations.
"""
from django.db import models
from django.db.models import Q
from django.utils.timezone import localtime
from datetime import timedelta
#from django.shortcuts import render_to_string
from django.template.loader import render_to_string
from .enums import DayOfWeek


class RequestManager(models.Manager):
    def is_available(self, item, start, end, repeat_on=0, end_repeating_on=None):
        request = Request(repeat_on=repeat_on)
        duration = end - start
        if end_repeating_on is None:
            end_repeating_on = end

        intervals = list(RequestInterval.objects.filter(
            Q(start__lte=end_repeating_on)|Q(end__lte=end_repeating_on)
        ).filter(
            Q(start__gte=start)|Q(end__gte=start)
        ).filter(
            request__item__pk=item.pk
        ).order_by("start"))

        # the best we can do here is O(n*lg(n)) (I think)
        intervals.extend(request.iter_intervals(start, end_repeating_on, duration))
        intervals.sort(key=lambda interval: (interval.start, interval.end))
        for index, interval in enumerate(intervals[:-1]):
            if interval.intersects(intervals[index+1]):
                return False
        return True


class Request(models.Model):
    request_id = models.AutoField(primary_key=True)
    # an enum value bitwise or-ing DayOfWeek
    repeat_on = models.IntegerField(default=0)

    created_on = models.DateTimeField(auto_now_add=True)
    edited_on = models.DateTimeField(auto_now=True)

    # the person who created the Request within the app
    created_by = models.ForeignKey("users.User", null=True, on_delete=models.SET_NULL, related_name="+")
    # the person who is actually requesting the item
    user = models.ForeignKey("users.User")
    # the item being reserved
    item = models.ForeignKey("items.Item")

    objects = RequestManager()

    class Meta:
        db_table = "request"

    def iter_intervals(self, start, end, duration):
        """
        Yields all the RequestInterval objects that would exist on this Request
        """
        intervals = []
        date = start
        while date <= end:
            if date == start or ((2**((date.weekday()+1) % 7)) & self.repeat_on):
                yield RequestInterval(start=date, end=date+duration)

            date += timedelta(days=1)


class RequestView(models.Model):
    """
    This makes it easy to retrieve the start and end date of a request, without
    doing extra queries, or relying on caching. This is not a real table. It's
    a database view
    """
    request = models.OneToOneField(Request, primary_key=True)
    first_interval = models.ForeignKey("RequestInterval", related_name="+", on_delete=models.DO_NOTHING)
    last_interval = models.ForeignKey("RequestInterval", related_name="+", on_delete=models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "request_view"


class RequestInterval(models.Model):
    """
    Represents a datetime for a particular Request
    """
    RESERVED = 1
    LOANED = 2
    RETURNED = 4

    request_interval_id = models.AutoField(primary_key=True)
    start = models.DateTimeField(help_text="Starting datetime of the request")
    end = models.DateTimeField(help_text="Ending datetime of the request")
    alma_request_id = models.CharField(max_length=255, help_text="The corresponding Alma Request ID")
    state = models.IntegerField(choices=(
        (RESERVED, "Reserved"),
        (LOANED, "Loaned"),
        (RETURNED, "Returned"),
    ), help_text="The state of this request", default=RESERVED)
    loaned_on = models.DateTimeField(null=True, default=None, help_text="When the item was actually loaned to the user")
    returned_on = models.DateTimeField(null=True, default=None, help_text="When the item was returned from the user")

    request = models.ForeignKey(Request, help_text="The parent request linking one or more intervals together")

    class Meta:
        db_table = "request_interval"

    @property
    def cache_key(self):
        # any mutable field that appears in the popover should be used to
        # create the cache key
        return "|".join(map(str,
            [self.pk, self.state]
        ))

    def intersects(self, other):
        #return (max(self.start, self.end) > min(other.start, other.end)) and (min(self.start, self.end) < max(other.start, other.end))
        return self.start < other.end and self.end > other.start

    def to_html(self):
        days = ""
        if self.request.repeat_on:
            days = str(DayOfWeek(self.request.repeat_on))

        form = RequestIntervalChangeForm(intervals=[self])
        return render_to_string("requests/_popover.html", {
            "form": form,
            "interval": self,
            "days": days,
        })

from .forms import RequestIntervalChangeForm
