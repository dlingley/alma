"""
The limitation with the Alma software is that it doesn't allow repeating
bookings/requests for an item. The whole point of *this* application is to get
around that. A Request here can have one or more days (RequestInterval)
associated with it. Thus, allowing for repeating reservations.
"""
from django.db import models

class Request(models.Model):
    request_id = models.AutoField(primary_key=True)

    created_on = models.DateTimeField(auto_now_add=True)
    edited_on = models.DateTimeField(auto_now=True)

    # the person who created the Request within the app
    created_by = models.ForeignKey("users.User", null=True, on_delete=models.SET_NULL)
    # the person who is actually requesting the item
    user = models.ForeignKey("users.User")
    # the item being reserved
    item = models.ForeignKey("items.Item")

    class Meta:
        db_table = "request"


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
    ), help_text="The state of this request")
    loaned_on = models.DateTimeField(null=True, default=None, help_text="When the item was actually loaned to the user")
    returned_on = models.DateTimeField(null=True, default=None, help_text="When the item was returned from the user")

    request = models.ForeignKey(Request, help_text="The parent request linking one or more intervals together")

    class Meta:
        db_table = "request_interval"
