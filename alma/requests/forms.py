import re
from django import forms
from alma.users.utils import is_ldap_user
from alma.users.models import User
from alma.items.models import Item, Bib
from alma.loans.models import Loan
from .models import Reservation, Request
from .enums import DayOfWeek


class OmniForm(forms.Form):
    """
    Handles checking in an item, loaning an item, or creating a reservation for a bib
    """
    user = forms.CharField(label="", required=False, widget=forms.widgets.TextInput(attrs={"placeholder": "ODIN Username"}))
    bibs_or_item = forms.CharField(label="", widget=forms.widgets.TextInput(attrs={"placeholder": "Item or Bib"}))

    starting_on = forms.DateTimeField(required=False)
    ending_on = forms.DateTimeField(required=False)

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

    def clean_user(self):
        """
        Makes sure the user is in LDAP, and creates the user in the system if
        it doesn't exist already

        The user is submitted as something like "Matt Johnson (mdj2)", so we
        have to parse out the "mdj2" part
        """
        user = self.cleaned_data['user'].strip()
        # if the user isn't filled out, so be it
        if user == "":
            return ""

        matches = re.search(r"\((.+)\)$", user)
        if not matches:
            raise forms.ValidationError("user must be of the form 'name (odin)'")

        user = matches.group(1)

        if not is_ldap_user(user):
            raise forms.ValidationError("Not a valid ODIN username")

        # create the user in the system if it doesn't exist
        email = User.username_to_email(user)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User(email=email, is_active=False)
            user.save()

        return user

    def clean_end_repeating_on(self):
        """Make the repeating_on datetime stretch to the end of the day"""
        return self.cleaned_data['end_repeating_on'].replace(hour=23, minute=59, second=59) if self.cleaned_data['end_repeating_on'] else None

    def clean_repeat_on(self):
        """Convert the list of repeat_on days to an integer"""
        return int(DayOfWeek.from_list(self.cleaned_data['repeat_on'] or []))

    def clean_bibs_or_item(self):
        val = self.cleaned_data['bibs_or_item']
        mms_id = re.search(r"\(MMS_ID: (.+)\)$", val)
        barcode = re.search(r"\(Barcode: (.+)\)$", val)
        if not barcode and not mms_id:
            raise forms.ValidationError("Not a valid barcode or MMS_ID")

        if mms_id:
            return [Bib.objects.get(mms_id=mms_id.group(1))]
        if barcode:
            return Item.objects.get(barcode=barcode.group(1))

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

        if cleaned_data.get("bibs_or_item") and isinstance(cleaned_data['bibs_or_item'], Bib) and self.cleaned_data.get("user", "") == "":
            self.add_error("user", "This field is required.")

        return cleaned_data

    def action_to_take_on_save(self):
        if isinstance(self.cleaned_data['bibs_or_item'], Item):
            if Loan.objects.filter(item=self.cleaned_data['bibs_or_item'], returned_on=None).exists():
                return "returning"
            else:
                return "loaning"
        else:
            return "reserving"

    def save(self, *args, created_by, **kwargs):
        action = self.action_to_take_on_save()
        if action == "returning":
            loans = Loan.objects.filter(item=self.cleaned_data['bibs_or_item'], returned_on=None)
            for loan in loans:
                loan.return_()
        elif action == "loaning":
            loan = Loan(item=self.cleaned_data['bibs_or_item'], user=self.cleaned_data['user'])
            loan.save()
        elif action == "reserving":
            for bib in self.cleaned_data['bibs_or_item']:
                reservation = Reservation(
                    created_by=created_by,
                    repeat_on=self.cleaned_data['repeat_on'],
                    user=self.cleaned_data['user'],
                    bib=bib,
                )
                reservation.save(
                    starting_on=self.cleaned_data['starting_on'],
                    ending_on=self.cleaned_data["ending_on"],
                    end_repeating_on=self.cleaned_data.get("end_repeating_on")
                )


class RequestChangeForm(forms.Form):
    THIS_RESERVATION = "1"
    THIS_AND_ALL_AFTER = "2"
    THE_ENTIRE_SERIES = "3"

    def __init__(self, *args, requests, **kwargs):
        super().__init__(*args, **kwargs)
        self.requests = requests
        for request in requests:
            self.fields["request-%s-delete" % request.pk] = forms.BooleanField(label="Delete?", initial=False, required=False)

            choices = [(self.THIS_RESERVATION, "This reservation")]
            if request.reservation.repeat_on:
                choices.extend([
                    (self.THIS_AND_ALL_AFTER, "This and all after it"),
                    (self.THE_ENTIRE_SERIES, "The entire series")
                ])

            self.fields["request-%s-delete-choice" % request.pk] = forms.ChoiceField(label="", required=False, choices=choices)

    def __iter__(self):
        for request in self.requests:
            yield request, self["request-%s-delete" % request.pk], self["request-%s-delete-choice" % request.pk]

    def save(self):
        for request in self.requests:
            if self.cleaned_data.get("request-%s-delete" % request.pk):
                delete_choice = self.cleaned_data.get("request-%s-delete-choice" % request.pk)
                if delete_choice == self.THIS_RESERVATION:
                    request.delete()
                elif delete_choice == self.THIS_AND_ALL_AFTER:
                    for r in Request.objects.filter(reservation_id=request.reservation_id, start__gte=request.start):
                        r.delete()
                elif delete_choice == self.THE_ENTIRE_SERIES:
                    Reservation.objects.get(reservation_id=request.reservation_id).delete()
