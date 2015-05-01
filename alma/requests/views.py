import copy
from collections import OrderedDict
from datetime import date, timedelta
from django.db.models import Q
from django.utils.timezone import now, localtime
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from alma.users.models import User
from .models import RequestInterval
from .forms import RequestForm, RequestIntervalChangeForm
from .utils import RequestIntervalContainerForTemplate

DAYS_TO_SHOW = 90

def main(request):
    """Display the main calendar view"""
    if request.method == "POST":
        form = RequestForm(request.POST)
        if form.is_valid():
            form.save(created_by=request.user)
            return redirect("home")
    else:
        form = RequestForm()

    return render(request, "requests/calendar.html", {
        "form": form,
    })


@csrf_exempt # TODO fix this
def change_status(request, request_interval_id):
    interval = get_object_or_404(RequestInterval, pk=request_interval_id)
    form = RequestIntervalChangeForm(request.POST, intervals=[interval])
    if form.is_valid():
        form.save()
    return HttpResponse()


def user(request):
    """
    Return the recent Requests Intervals for this user, or ones that have been
    checked out
    """
    email = User.username_to_email(request.GET.get("username", ""))
    intervals = RequestInterval.objects.filter(request__user__email=email).filter(Q(
        end__lte=now()+timedelta(hours=8),
        end__gte=now()
        ) | Q(state=RequestInterval.LOANED)
    ).select_related(
        "request",
        "request__item",
        "request__user",
        "request__requestview__first_interval",
        "request__requestview__last_interval"
    )

    return render(request, "requests/_user.html", {
        "intervals": intervals,
    })


def available(request):
    """
    This is a little hacky, but it checks to see if the
    """
    if request.method == "POST":
        data = request.POST.copy()
        data['user'] = request.user.username
        form = RequestForm(data)
        if form.is_valid():
            return HttpResponse("available")
        elif [error for error in form.errors.as_data().get("__all__", []) if error.code == "unavailable"]:
            return HttpResponse("unavailable")
        print(form.errors)
    return HttpResponse("notvalid")


def calendar(request):
    # get the first Sunday of the week
    try:
        page = int(request.GET.get("page", 0))
    except (TypeError, ValueError) as e:
        page = 0

    start_date = date.today() - timedelta(days=(date.today().weekday()+1)) + timedelta(days=page*DAYS_TO_SHOW)

    # `calendar` is a ordereddict where the key is a date object (of the first of
    # the month), and the value is an ordered dict where the key is a date, and
    # the value is a RequestIntervalContainerForTemplate object
    calendar = OrderedDict()
    day = start_date

    # initialize all the days in the calendar
    for i in range(DAYS_TO_SHOW):
        month = day.replace(day=1)
        if month not in calendar:
            calendar[month] = OrderedDict()

        calendar[month][day] = RequestIntervalContainerForTemplate(day=day)
        day += timedelta(days=1)

    # the end_date is one day ahead of where we want to stop. That's OK, since
    # we'll use the less-than operator, instead of less-than-or-equal-to
    # in the queryset filter below
    end_date = day

    # find all the RequestIntervals in this date range
    intervals = list(RequestInterval.objects.filter(
        end__lt=end_date,
        start__gte=start_date
    ).select_related(
        "request",
        "request__item",
        "request__user",
        "request__requestview",
        "request__requestview__first_interval",
        "request__requestview__last_interval"
    ).order_by("pk"))

    i = 0
    while i < len(intervals):
        interval = intervals[i]
        # Get the right RequestIntervalList object from the calendar
        start = localtime(interval.start)
        end = localtime(interval.end)
        request_interval_list = calendar[start.date().replace(day=1)][start.date()]

        # we need to split this interval into two pieces
        if end.date() > start.date():
            new_request_interval = copy.copy(interval)
            new_request_interval.start = start.replace(hour=0, minute=0, second=0)+timedelta(days=1)
            new_request_interval.parent = interval
            intervals.append(new_request_interval)

            end = start.replace(hour=23, minute=59, second=59)

        request_interval_list.add(interval)
        i += 1


    hours = ["12am"] + [t+"am" for t in map(str, range(1, 12))] + ["12pm"] + [t+"pm" for t in map(str, range(1, 12))]
    return render(request, "requests/_calendar.html", {
        "calendar": calendar,
        "hours": hours,
        "today": date.today(),
        "page": page,
        "next_page": page+1,
        "previous_page": page-1,
        "intervals": intervals,
    })
