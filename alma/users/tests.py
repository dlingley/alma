from datetime import date
from unittest.mock import Mock, patch

from django.core.urlresolvers import reverse
from django.test import TestCase
from model_mommy.mommy import make, prepare

from .forms import UserForm
from .models import User
from .perms import permissions
from .utils import is_ldap_user
from .views import detail

thing = lambda date, repeat_on: (2**((date.weekday()+1)%7)) & repeat_on

class TestThing(TestCase):
    def test(self):
        self.assertTrue(thing(date(year=2015, month=4, day=19), 1))
        self.assertTrue(thing(date(year=2015, month=4, day=20), 2))
        self.assertTrue(thing(date(year=2015, month=4, day=21), 4))
        self.assertTrue(thing(date(year=2015, month=4, day=22), 8))
        self.assertTrue(thing(date(year=2015, month=4, day=23), 16))
        self.assertTrue(thing(date(year=2015, month=4, day=24), 32))
        self.assertTrue(thing(date(year=2015, month=4, day=25), 64))


class IsLdapUserTest(TestCase):
    def test(self):
        with patch("alma.users.utils.ldapsearch", return_value=['mdj2']):
            self.assertTrue(is_ldap_user("mdj2"))
        with patch("alma.users.utils.ldapsearch", return_value=[]):
            self.assertFalse(is_ldap_user("mdj2222"))

class DetailViewTest(TestCase):
    """
    Tests for the detail view
    """
    def test_permission(self):
        self.assertTrue(permissions.entry_for_view(detail, 'can_view_user'))

    def test_get(self):
        user = prepare(User)
        user.set_password("foobar")
        user.save()
        self.client.login(email=user.email, password="foobar")
        self.client.get(reverse("users-detail", args=[user.pk]))


class UserFormTest(TestCase):
    """
    Tests for the UserForm
    """
    def test_password_field_only_when_user_being_created(self):
        """
        The password field should only be on the form if the user is being
        created (not edited)
        """
        form = UserForm(user=prepare(User))
        self.assertIn("password", form.fields)

        form = UserForm(instance=make(User), user=prepare(User))
        self.assertNotIn("password", form.fields)

    def test_your_dangerous_fields_are_not_editable(self):
        """
        Fields like is_active and is_staff should not be changable if the user
        is editing himself
        """
        user = make(User, is_staff=True)
        form = UserForm(user=user, instance=user)
        self.assertNotIn("is_active", form.fields)
        self.assertNotIn("is_staff", form.fields)

        # if someone is editing someone else, they can update those fields
        other_user = make(User)
        form = UserForm(instance=other_user, user=user)
        self.assertIn("is_active", form.fields)
        self.assertIn("is_staff", form.fields)

    def test_non_staffers_cannot_set_some_fields(self):
        """
        Some fields should not be editable by non-staffers
        """
        user = make(User, is_staff=False)
        form = UserForm(user=user, instance=user)
        self.assertNotIn("is_staff", form.fields)

    def test_save_sets_the_password_for_new_users(self):
        """
        If the user is being created, the password should be updated
        """
        # to avoid having to generate valid data for this form, we mock up the
        # superclass's save method and the form's cleaned_data
        with patch("alma.users.forms.forms.ModelForm.save") as mock:
            user = prepare(User)
            form = UserForm(instance=user, user=make(User))
            form.cleaned_data = {"password": "foobar"}

            form.save()

            self.assertTrue(user.check_password("foobar"))
            # ensure the superclass was called (which actually saves the model)
            self.assertTrue(mock.called)


class UserTest(TestCase):
    """
    Tests for the User model
    """
    def test_str(self):
        user = prepare(User, first_name="foo", last_name="bar")
        self.assertEqual(str(user), "bar, foo")
        # the str method should fall back on the email address if a part of
        # their name is blank
        user = prepare(User, first_name="", last_name="bar")
        self.assertEqual(str(user), user.email)

    def test_get_full_name(self):
        user = prepare(User, first_name="foo", last_name="bar")
        self.assertEqual(user.get_full_name(), "bar, foo")

    def test_get_short_name(self):
        user = prepare(User, first_name="foo", last_name="bar")
        self.assertEqual(user.get_short_name(), "foo bar")

    def test_has_perm(self):
        """Staff members have all Django admin perms"""
        user = prepare(User, is_staff=False)
        self.assertFalse(user.has_perm("foo"), user)

        user = prepare(User, is_staff=True)
        self.assertTrue(user.has_perm("foo"), user)

    def test_has_module_perms(self):
        """Staff members have all Django admin perms"""
        user = prepare(User, is_staff=False)
        self.assertFalse(user.has_module_perms("foo"), user)

        user = prepare(User, is_staff=True)
        self.assertTrue(user.has_module_perms("foo"), user)

    def test_can_cloak_as(self):
        """Only staffers can cloak"""
        user = prepare(User, is_staff=False)
        self.assertFalse(user.has_module_perms("foo"), user)

        user = prepare(User, is_staff=True)
        self.assertTrue(user.has_module_perms("foo"), user)
