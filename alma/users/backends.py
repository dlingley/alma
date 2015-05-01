import sys, os
from arcutils import ldap
from djangocas.backends import CASBackend
from django.core.exceptions import PermissionDenied
from .models import User

LOGIN_GROUPS = ['arc']

class PSUBackend(CASBackend):
    def get_or_init_user(self, username):
        # make sure this user is in the required group
        groups = self.get_groups(username)
        if set(groups) & set(LOGIN_GROUPS) == set():
            raise PermissionDenied("You need to belong to a group in LOGIN_GROUPS")

        email = username + "@pdx.edu"
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            profile = self.get_profile(username)
            user = User(email=email, first_name=profile['first_name'], last_name=profile['last_name'], is_active=True, is_staff=False)
            user.set_unusable_password()
            user.save()

        return user

    def get_profile(self, username):
        results = ldap.ldapsearch("(uid=" + ldap.escape(username) + ")")
        dn, entry = results[0]
        profile = ldap.parse_profile(entry)
        return profile

    def get_groups(self, username):
        """
        Method to get the groups the user is involved in.
        Calls an LDAP search.
        Returns a list of groups.
        """
        results = ldap.ldapsearch("(& (memberUid=" + ldap.escape(username) + ") (cn=*))")
        groups = [result[1]['cn'][0] for result in results]
        return groups
