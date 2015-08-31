import copy
from collections import OrderedDict
from datetime import timedelta
from itertools import chain

from django.utils.timezone import localtime, now

NUMBER_OF_SECONDS_IN_A_DAY = 60*60*24
PERCENTS_PER_SECOND = 100.0/NUMBER_OF_SECONDS_IN_A_DAY


class CalendarItem:
    """
    This provides an interface to display Loan objects or Request objects on
    the calendar
    """
    @classmethod
    def from_request(cls, request):
        """Create an instance of this class from a Request object"""
        return cls(
            start=request.start,
            end=request.end,
            user=request.reservation.user,
            bib=request.reservation.bib,
            model=request,
        )

    @classmethod
    def from_loan(cls, loan):
        """Create an instance of this class from a Loan object"""
        return cls(
            start=loan.loaned_on,
            # since the loan hasn't been returned, it's end date is whatever
            # the current time is
            end=now(),
            user=loan.user,
            item=loan.item,
            model=loan,
        )

    def __init__(self, model, start, end, user, item=None, bib=None, parent=None):
        # datetime objects need to be converted to localtime so .date() works
        # as expected
        self.start = localtime(start)
        self.end = localtime(end)

        self.user = user
        self.item = item
        self.bib = bib
        self.model = model
        # If this CalendarItem gets split up because it spans multiple days,
        # this `parent` attribute references the parent CalendarItem it was
        # split from. The object itself isn't that useful, but just knowing this CalendarItem
        # was split is useful for styling it
        self.parent = parent

        # this is set by the CalendarItemContainerForTemplate
        self.css = None

    def intersects(self, other):
        return self.start < other.end and self.end > other.start

    def escaped_html(self):
        # the html for the CalendarItem is rendered in a bootstrap popover
        # which expects the HTML to be in a "data-content" attribute. Since
        # this HTML is contained within quotes, we need to escape the
        # quotes.
        return self.model.to_html().replace('"', "\"")

    def split(self):
        new_request = copy.copy(self)
        new_request.start = self.start.replace(hour=0, minute=0, second=0, microsecond=0)+timedelta(days=1)
        new_request.parent = self
        return new_request


class CalendarItemContainerForTemplate:
    """
    This is a special container for CalendarItem objects on a particular
    day. When a CalendarItem is added to the list, this object will augment
    the CalendarItem object with the appropriate CSS
    """
    def __init__(self, day):
        # calendar_items are stored as an OrderedDict where the key is a "level"
        # integer, and the value is a list of CalendarItem objects. When
        # calendar_items on this day overlap, we add another level, and stick the
        # CalenderItem on that level. This helps position the items on the
        # page so they don't overlap
        self.calendar_items = OrderedDict({0: []})

        # this is the default height for a row on the calendar. It may need
        # to expand if there lots of calendar_item collisions on this day
        self.min_height = 30

        # this is the height of an calendar_item bar on the calendar
        self.calendar_item_height = 15

        # we use the day as part of the cache key generated in the __str__
        # method
        self.day = day

    @property
    def height(self):
        # we need to know how big to make the row on this day. If it has a
        # bunch of collisions, it will grow bigger than the default height
        return max(self.min_height, self.calendar_item_height*(len(self.calendar_items)))

    def __iter__(self):
        return iter(chain(*self.calendar_items.values()))

    def __str__(self):
        """
        We use this object in a template fragment cache, so the string
        method needs to represent this object's state
        """
        string = str(self.day) + "|" + "|".join(item.cache_key for item in self)
        return string

    def default_css(self, calendar_item):
        """
        Returns a dict of the default css properties for this calendar_item
        """
        start = localtime(calendar_item.start)
        end = localtime(calendar_item.end)

        percent_from_left = (start - start.replace(hour=0, minute=0, second=0)).total_seconds() * PERCENTS_PER_SECOND
        percent_width = (end - start).total_seconds() * PERCENTS_PER_SECOND
        # if this calendar_item spans more than a day, cut it off at the end of the day
        percent_width = max(1, min(percent_width, 100.0 - percent_from_left))

        return {
            "width": str(percent_width) + "%",
            "left": str(percent_from_left) + "%",
            "height": str(self.calendar_item_height) + "px",
        }

    def add_to_level(self, calendar_item):
        level = 0
        for level, calendar_items in self.calendar_items.items():
            for other_calendar_item in calendar_items:
                if calendar_item.intersects(other_calendar_item):
                    level += 1
                    break
            else:
                self.calendar_items.setdefault(level, []).append(calendar_item)

    def add(self, calendar_item):
        """
        This adds a CalendarItem to this object's calendar_item collection of them and
        sets a bunch of properties on the object for use in the template
        """
        # we need to detect collisions on the calendar. We start off with one
        # "level". If there is a collision between calendar_items, we put the
        # calendar_item on the next level down. When it's all done, we use the level
        # to determine how much margin to add to the calendar_item when it is
        # displayed on the page so it doesn't overlap other calendar_items
        for level in range(len(self.calendar_items)+1):
            calendar_items = self.calendar_items.setdefault(level, [])
            for other_calendar_item in calendar_items:
                if calendar_item.intersects(other_calendar_item):
                    level += 1
                    break
            else:
                calendar_items.append(calendar_item)
                break

        css = self.default_css(calendar_item)
        css['margin-top'] = str(level*self.calendar_item_height) + "px"

        # generate the CSS as a string
        calendar_item.css = ";".join("%s:%s" % rule for rule in css.items())
