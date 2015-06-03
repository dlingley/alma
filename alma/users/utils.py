from arcutils.ldap import escape, ldapsearch


def is_ldap_user(username):
    """
    Checks LDAP to ensure a user name exists.
    """
    q = escape(username)
    search = '(uid={q})'.format(q=q)
    return bool(ldapsearch(search))
