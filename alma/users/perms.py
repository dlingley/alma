from .models import User
from ..perms import permissions


@permissions.register
def can_create_user(user):
    # only staffers can create users
    return user.is_staff


@permissions.register(model=User)
def can_edit_user(user, other_user):
    # you can edit yourself
    if user.pk == other_user.pk:
        return True

    # staffers can edit anyone
    if user.is_staff:
        return True


@permissions.register
def can_list_users(user):
    # only staffers can list all the users
    return user.is_staff


@permissions.register(model=User)
def can_delete_user(user, other_user):
    # you can't delete yourself!
    if user.pk == other_user.pk:
        return False

    # staffers can delete users
    return user.is_staff


@permissions.register(model=User)
def can_view_user(user, other_user):
    # you can always view yourself
    if user.pk == other_user.pk:
        return True

    # staffers can view any user
    return user.is_staff
