from datetime import date, timedelta
from django.utils.timezone import now
from django.shortcuts import render, redirect

def calendar(request):
    # get the first Sunday of the week
    try:
        week_offset = int(request.GET.get("week_offset", 0))
    except (TypeError, ValueError) as e:
        week_offset = 0

    start_date = date.today() - timedelta(days=(date.today().weekday()+1)) + timedelta(days=week_offset*7)

    dates = [start_date]
    for i in range(6):
        dates.append(dates[-1] + timedelta(days=1))

    hours = ["12am"] + [t+"am" for t in map(str, range(1, 12))] + ["12pm"] + [t+"pm" for t in map(str, range(1, 12))]

    return render(request, "requests/calendar.html", {
        "dates": dates,
        "hours": hours,
        "today": date.today(),
        "week_offset": week_offset,
        "next_week_offset": week_offset+1,
        "previous_week_offset": week_offset-1,
    })
