from django.utils.timezone import localtime
from itertools import chain
from collections import OrderedDict

NUMBER_OF_SECONDS_IN_A_DAY = 60*60*24
PERCENTS_PER_SECOND = 100.0/NUMBER_OF_SECONDS_IN_A_DAY

class RequestIntervalContainerForTemplate:
    """
    This is a special container for RequestInterval objects on a particular
    day. When an interval is added to the list, this object will augment
    the RequestInterval object with a few attributes necessary to render
    the interval on a template.
    """
    def __init__(self, day):
        # intervals are stored as an OrderedDict where the key is a "level"
        # integer, and the value is a list of RequestInterval objects. When
        # intervals on this day overlap, we add another level, and stick the
        # RequestInterval on that level. This helps position the items on the
        # page so they don't overlap
        self.intervals = OrderedDict({0: []})

        # this is the default height for a row on the calendar. It may need
        # to expand if there lots of interval collisions on this day
        self.min_height = 30

        # this is the height of an interval bar on the calendar
        self.interval_height = 15;

        # we use the day as part of the cache key generated in the __str__
        # method
        self.day = day

    @property
    def height(self):
        # we need to know how big to make the row on this day. If it has a
        # bunch of collisions, it will grow bigger than the default height
        return max(self.min_height, self.interval_height*(len(self.intervals)))

    def __iter__(self):
        return iter(chain(*self.intervals.values()))

    def __str__(self):
        """
        We use this object in a template fragment cache, so the string
        method needs to represent this object's state
        """
        string = str(self.day) + "|" + "|".join(item.cache_key for item in self)
        return string

    def default_css(self, interval):
        """
        Returns a dict of the default css properties for this interval
        """
        start = localtime(interval.start)
        end = localtime(interval.end)

        percent_from_left = (start - start.replace(hour=0, minute=0, second=0)).total_seconds() * PERCENTS_PER_SECOND
        percent_width = (end - start).total_seconds() * PERCENTS_PER_SECOND
        # if this interval spans more than a day, cut it off at the end of the day
        percent_width = min(percent_width, 100.0 - percent_from_left)

        return {
            "width": str(percent_width) + "%",
            "left": str(percent_from_left) + "%",
            "height": str(self.interval_height) + "px",
        }

    def add_to_level(self, interval):
        level = 0
        for level, intervals in self.intervals.items():
            for other_interval in intervals:
                if interval.intersects(other_interval):
                    level += 1
                    break
            else:
                self.intervals.setdefault(level, []).append(interval)



    def add(self, interval):
        """
        This adds an interval to this object's interval collection of them and
        sets a bunch of properties on the object for use in the template
        """
        # we need to detect collisions on the calendar. We start off with one
        # "level". If there is a collision between intervals, we put the
        # interval on the next level down. When it's all done, we use the level
        # to determine how much margin to add to the interval when it is
        # displayed on the page so it doesn't overlap other intervals
        for level in range(len(self.intervals)+1):
            intervals = self.intervals.setdefault(level, [])
            for other_interval in intervals:
                if interval.intersects(other_interval):
                    level += 1
                    break
            else:
                intervals.append(interval)
                break

        css = self.default_css(interval)
        css['margin-top'] = str(level*self.interval_height) + "px"

        # generate the CSS as a string
        interval.css = ";".join("%s:%s" % rule for rule in css.items())

        # the html for the interval is rendered in a bootstrap popover
        # which expects the HTML to be in a "data-content" attribute. Since
        # this HTML is contained within quotes, we need to escape the
        # quotes. Also, we don't want to call to_html() unless we really
        # need to (since this may be rendered in a cached template
        # fragment), which is why we wrap it up in a lambda
        interval.escaped_html = lambda interval=interval: interval.to_html().replace('"', "\"")

        #self.intervals.append(interval)


