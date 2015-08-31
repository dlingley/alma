from datetime import date
from unittest.mock import Mock, patch

from django.core.urlresolvers import reverse
from django.test import TestCase
from model_mommy.mommy import make, prepare

from .forms import UserForm
from .models import User
from .perms import permissions
from .utils import is_ldap_user

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
