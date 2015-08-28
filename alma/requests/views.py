from collections import OrderedDict
from datetime import date, timedelta

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now, localtime
from django.contrib.auth.decorators import login_required

from alma.alma.api import is_available
from alma.loans.models import Loan
from alma.users.models import User

from .forms import OmniForm, RequestChangeForm
from .models import Request, iter_intervals
from .utils import CalendarItem, CalendarItemContainerForTemplate

DAYS_TO_SHOW = 90


@login_required
def main(request):
    """Display the main calendar view"""
    if request.method == "POST":
        form = OmniForm(request.POST)
        if form.is_valid():
            form.save(created_by=request.user)
            return redirect("home")
    else:
        form = OmniForm()

    return render(request, "requests/calendar.html", {
        "form": form,
    })


@csrf_exempt # TODO fix this
@login_required
def change_status(request, request_id):
    req = get_object_or_404(Request, pk=request_id)
    form = RequestChangeForm(request.POST, requests=[req])
    if form.is_valid():
        form.save()
    return HttpResponse()


@login_required
def user(request):
    """
    Return the recent Requests Intervals for this user, or ones that have been
    checked out
    """
    email = User.username_to_email(request.GET.get("username", ""))
    requests = Request.objects.filter(reservation__user__email=email).filter(
        end__lte=now()+timedelta(hours=10000),
        end__gte=now()
    ).select_related(
        "reservation",
        "reservation__bib",
        "reservation__user",
    )

    return render(request, "requests/_user.html", {
        "requests": requests,
    })


@login_required
def available(request):
    """
    This is a little hacky, but it checks to see if the
    """
    if request.method == "POST":
        form = OmniForm(request.POST)
        form.is_valid()
        # these are the fields that need to be valid if we can successfully check for availability
        necessary_fields = ['bibs_or_item', 'starting_on', 'ending_on', 'repeat', 'repeat_on', 'end_repeating_on']
        for field in necessary_fields:
            if field in form.errors:
                return HttpResponse("notvalid")

        # these fields must not be falsy
        truthy_fields = ['starting_on', 'ending_on']
        for field in truthy_fields:
            if not form.cleaned_data.get(field):
                return HttpResponse("notvalid")

        if form.action_to_take_on_save() != "reserving":
                return HttpResponse("notvalid")

        intervals = list(iter_intervals(
            form.cleaned_data['starting_on'],
            form.cleaned_data['ending_on'],
            form.cleaned_data['end_repeating_on'],
            form.cleaned_data['repeat_on']
        ))

        output = []
        for interval in intervals:
            output.append({
                "start": interval[0],
                "end": interval[1],
                "items": []
            })

        for bib in form.cleaned_data['bibs_or_item']:
            results = list(is_available(bib.mms_id, intervals))
            for data, is_avail in zip(output, results):
                data['items'].append({"name": str(bib), "is_available": is_avail})

        return render(request, "requests/_availability.html", {
            "request_blocks": output,
        })

    return HttpResponse("notvalid")


@login_required
def calendar(request):
    # get the first Sunday of the week
    try:
        page = int(request.GET.get("page", 0))
    except (TypeError, ValueError):
        page = 0

    today = localtime(now())
    start_date = today - timedelta(days=(today.date().weekday()+1)) + timedelta(days=page*DAYS_TO_SHOW)

    # `calendar` is a ordereddict where the key is a date object (of the first of
    # the month), and the value is an ordered dict where the key is a date, and
    # the value is a CalendarItemContainerForTemplate object
    calendar = OrderedDict()
    day = start_date

    # initialize all the days in the calendar
    for i in range(DAYS_TO_SHOW):
        month = day.replace(day=1).date()
        if month not in calendar:
            calendar[month] = OrderedDict()

        calendar[month][day.date()] = CalendarItemContainerForTemplate(day=day.date())
        day += timedelta(days=1)

    # the end_date is one day ahead of where we want to stop. That's OK, since
    # we'll use the less-than operator, instead of less-than-or-equal-to
    # in the queryset filter below
    end_date = day

    # find all the Requests in this date range, and convert them into CalendarItem objects
    calendar_items = [CalendarItem.from_request(req) for req in Request.objects.filter(
        end__lt=end_date,
        start__gte=start_date
    ).select_related(
        "reservation",
        "reservation__bib",
        "reservation__user",
    ).order_by("pk")]

    # do the same for Loan objects
    calendar_items.extend(CalendarItem.from_loan(loan) for loan in Loan.objects.filter(
        returned_on=None,
        loaned_on__gte=start_date,
        loaned_on__lt=end_date
    ).select_related("item", "user", "item__bib"))

    i = 0
    while i < len(calendar_items):
        calendar_item = calendar_items[i]
        request_list = calendar[calendar_item.start.date().replace(day=1)][calendar_item.start.date()]

        # we need to split this calendar_item into two pieces since it spans multiple days
        if calendar_item.end.date() > calendar_item.start.date():
            calendar_items.append(calendar_item.split())

        request_list.add(calendar_item)
        i += 1

    hours = ["12am"] + [t+"am" for t in map(str, range(1, 12))] + ["12pm"] + [t+"pm" for t in map(str, range(1, 12))]
    return render(request, "requests/_calendar.html", {
        "calendar": calendar,
        "hours": hours,
        "today": today.date(),
        "page": page,
        "next_page": page+1,
        "previous_page": page-1,
        "intervals": calendar_items,
    })
