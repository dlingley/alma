class DayOfWeek:
    """
    This is a wonky class for handling days of the week. The days of the week
    is stored as an integer in the DB, which makes some things easier, and some
    things harder.

    The attributes on this class are OR'd together to form the numeric
    representation of those days.
    """
    SUNDAY = 1
    MONDAY = 2
    TUESDAY = 4
    WEDNESDAY = 8
    THURSDAY = 16
    FRIDAY = 32
    SATURDAY = 64

    attrs = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]

    def __init__(self, value):
        """Takes a value like 3 which is a representation for Sunday (1) and Monday (2)"""
        self.value = value

    def __iter__(self):
        """Iterates over the integer values for all the days this represents"""
        for key in self.attrs:
            if self.value and getattr(self, key) & self.value:
                yield getattr(self, key)

    def __int__(self):
        return self.value

    def __str__(self):
        """
        str(DayOfWeek(3)) == "Mon, Tue"
        """
        string = []
        for key in self.attrs:
            if self.value and getattr(self, key) & self.value:
                string.append(key.capitalize()[:3])

        return ", ".join(string)

    @classmethod
    def from_list(cls, items):
        """
        Takes a list of numbers like [1, 2, 4] and bit ORs them together and
        returns DayOfWeek(that_number)
        """
        bit = 0
        for number in items:
            bit |= int(number)
        return cls(bit)
