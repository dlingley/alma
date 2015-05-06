import re
from datetime import timedelta
from django.utils.timezone import now
from django import forms
from alma.users.utils import is_ldap_user
from alma.users.models import User
from alma.items.models import Item
from .models import Request, DayOfWeek, RequestInterval
from .enums import DayOfWeek

class RequestForm(forms.ModelForm):
    user = forms.CharField(label="", widget=forms.widgets.TextInput(attrs={"placeholder": "ODIN Username"}))
    item = forms.CharField(label="", widget=forms.widgets.TextInput(attrs={"placeholder": "Item"}))
    starting_on = forms.DateTimeField()
    ending_on = forms.DateTimeField()

    repeat = forms.BooleanField(required=False)
    repeat_on = forms.MultipleChoiceField(choices=(
        (DayOfWeek.SUNDAY, "Su"),
        (DayOfWeek.MONDAY, "M"),
        (DayOfWeek.TUESDAY, "T"),
        (DayOfWeek.WEDNESDAY, "W"),
        (DayOfWeek.THURSDAY, "Th"),
        (DayOfWeek.FRIDAY, "F"),
        (DayOfWeek.SATURDAY, "Sa"),
    ), widget=forms.CheckboxSelectMultiple, required=False)

    end_repeating_on = forms.DateTimeField(required=False)

    class Meta:
        model = Request
        fields = [
            'repeat_on',
            'user',
            'item',
        ]

    def clean_user(self):
        """
        Makes sure the user is in LDAP, and creates the user in the system if
        it doesn't exist already

        The user is submitted as something like "Matt Johnson (mdj2)", so we
        have to parse out the "mdj2" part
        """
        user = self.cleaned_data['user'].strip()
        matches = re.search(r"\((.+)\)$", user)
        if not matches:
            raise forms.ValidationError("user must be of the form 'name (odin)'")

        user = matches.group(1)

        if not is_ldap_user(user):
            raise forms.ValidationError("Not a valid ODIN username")

        # create the user in the system if it doesn't exist
        email = email=User.username_to_email(user)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User(email=email, is_active=False)
            user.save()

        return user

    def clean_item(self):
        """
        Ensures the item exists in the system

        The item is submitted as something like "VGA Cable (1234abc)", so we
        have to parse out the "1234abc" part
        """
        item = self.cleaned_data['item'].strip()
        matches = re.search(r"\((.+)\)$", item)
        if not matches:
            raise forms.ValidationError("Item must be of the form 'item name (item_id)'")

        item = matches.group(1)
        try:
            item = Item.objects.get(pk=item)
        except Item.DoesNotExist:
            raise forms.ValidationError("Item does not exist")

        return item

    def clean_end_repeating_on(self):
        """Make the repeating_on datetime stretch to the end of the day"""
        return self.cleaned_data['end_repeating_on'].replace(hour=23, minute=59, second=59) if self.cleaned_data['end_repeating_on'] else None

    def clean_repeat_on(self):
        """Convert the list of repeat_on days to an integer"""
        return int(DayOfWeek.from_list(self.cleaned_data['repeat_on'] or []))

    def clean(self):
        cleaned_data = super().clean()
        # certain fields are required if repeat is turned on
        if cleaned_data.get("repeat"):
            if not cleaned_data.get("repeat_on"):
                self.add_error("repeat_on", "Please select the days to repeat")
            if not cleaned_data.get("end_repeating_on"):
                self.add_error("end_repeating_on", "Please choose when to stop the repeating")
        else:
            # get rid of these fields since they aren't relevant if we're not
            # repeating
            cleaned_data['repeat_on'] = 0
            cleaned_data["end_repeating_on"] = None

        # obviously, the start date can't be after the end date
        if cleaned_data.get('starting_on') and cleaned_data.get("ending_on") and cleaned_data['starting_on'] >= cleaned_data['ending_on']:
            self.add_error("starting_on", "This needs to be less than the ending on date")

        # the end repeating_on date must be greater than the starting_on date
        if cleaned_data.get("starting_on") and cleaned_data.get("end_repeating_on") and cleaned_data["starting_on"] >= cleaned_data['end_repeating_on']:
            self.add_error('end_repeating_on', "The end repeating on date must be greater than the starting on date")

        if not self._errors:
            if not Request.objects.is_available(cleaned_data['item'], cleaned_data['starting_on'], cleaned_data['ending_on'], cleaned_data['repeat_on'], cleaned_data["end_repeating_on"]):
                raise forms.ValidationError("That day is not available", code="unavailable")

        return cleaned_data

    def save(self, *args, created_by, **kwargs):
        self.instance.created_by = created_by

        to_return = super().save(*args, **kwargs)

        # create all the RequestInterval objects for this thing
        RequestInterval.objects.filter(request=self.instance).delete()
        start = self.cleaned_data['starting_on']
        end = self.cleaned_data["end_repeating_on"] or self.cleaned_data['ending_on']
        duration = self.cleaned_data['ending_on'] - start
        intervals = []
        for interval in self.instance.iter_intervals(start, end, duration):
            interval.state = RequestInterval.RESERVED
            interval.request = self.instance
            intervals.append(interval)

        RequestInterval.objects.bulk_create(intervals)
        return to_return


class RequestIntervalChangeForm(forms.Form):
    THIS_RESERVATION = "1"
    THIS_AND_ALL_AFTER = "2"
    THE_ENTIRE_SERIES = "3"

    def __init__(self, *args, intervals, **kwargs):
        super().__init__(*args, **kwargs)
        self.intervals = intervals
        for interval in intervals:
            self.fields["interval-%d" % interval.pk] = forms.ChoiceField(choices=[
                (RequestInterval.RESERVED, "Reserved"),
                (RequestInterval.LOANED, "Loaned"),
                (RequestInterval.RETURNED, "Returned"),
            ], initial=interval.state, widget=forms.widgets.RadioSelect)

            self.fields["interval-%d-delete" % interval.pk] = forms.BooleanField(label="Delete?", initial=False, required=False)

            choices = [(self.THIS_RESERVATION, "This reservation")]
            if interval.request.repeat_on:
                choices.extend([
                    (self.THIS_AND_ALL_AFTER, "This and all after it"),
                    (self.THE_ENTIRE_SERIES, "The entire series")
                ])

            self.fields["interval-%d-delete-choice" % interval.pk] = forms.ChoiceField(label="", required=False, choices=choices)

    def __iter__(self):
        for interval in self.intervals:
            yield interval, self["interval-%d" % interval.pk], self["interval-%d-delete" % interval.pk], self["interval-%d-delete-choice" % interval.pk]

    def save(self):
        for interval in self.intervals:
            if self.fields["interval-%d" % interval.pk].initial != self.cleaned_data["interval-%d" % interval.pk]:
                interval.state = self.cleaned_data['interval-%d' % interval.pk]
                if interval.state == RequestInterval.LOANED:
                    interval.loaned_on = now()
                elif interval.state == RequestInterval.RETURNED:
                    interval.returned_on = now()

                interval.save()

        for interval in self.intervals:
            if self.cleaned_data.get("interval-%d-delete" % interval.pk):
                delete_choice = self.cleaned_data.get("interval-%d-delete-choice" % interval.pk)
                if delete_choice == self.THIS_RESERVATION:
                    interval.delete()
                elif delete_choice == self.THIS_AND_ALL_AFTER:
                    RequestInterval.objects.filter(request_id=interval.request_id, start__gte=interval.start).delete()
                elif delete_choice == self.THE_ENTIRE_SERIES:
                    Request.objects.get(request_id=interval.request_id).delete()
