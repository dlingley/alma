from arcutils import will_be_deleted_with

from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .forms import UserForm
from .models import User
from .perms import permissions, can_list_users


@login_required
def home(request):
    """
    Just redirect to the detail view for the user. This page exists solely
    because settings.LOGIN_REDIRECT_URL needs to redirect to a "simple" URL
    (i.e. we can't use variables in the URL)
    """
    return redirect("users-detail", request.user.pk)


@permissions.can_view_user
def detail(request, user_id):
    """
    A nice homepage for user the user. By passing the user_id as a parameter,
    this allows admins to view the user's detail page, without having to
    masquerade as them.
    """
    user = get_object_or_404(User, pk=user_id)

    return render(request, "users/detail.html", {
        # we use the name "the_user" to avoid clashing with the authentication
        # context processor which populates the "user" template variable
        "the_user": user,
        # we hide the masquerade button if the user can't do it, or they are
        # looking at their own detail page
        "can_cloak": request.user.can_cloak_as(user) and user.pk != request.user.pk
    })


@permissions.can_list_users
def list_(request):
    """
    List out all the users in the system
    """
    users = User.objects.all()
    paginator = Paginator(users, settings.ITEMS_PER_PAGE)
    page = request.GET.get('page')
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        users = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        users = paginator.page(paginator.num_pages)

    return render(request, "users/list.html", {
        "users": users,
    })


@permissions.can_delete_user
def delete(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        user.delete()
        messages.success(request, "User deleted!")
        return redirect("users-list")

    related_objects = will_be_deleted_with(user)

    return render(request, "users/delete.html", {
        # we don't call this template variable "user" because that collides
        # with the "user" variable which references the currently logged in
        # user
        "object": user,
        "related_objects": related_objects,
    })


@permissions.can_create_user
def create(request):
    """
    Create a new user
    """
    return _edit(request)


@permissions.can_edit_user
def edit(request, user_id):
    """
    Edit an existing user.
    """
    user = get_object_or_404(User, pk=user_id)
    return _edit(request, user)


def _edit(request, user=None):
    """
    Handle creating or editing a user
    """
    if request.POST:
        form = UserForm(request.POST, user=request.user, instance=user)
        if form.is_valid():
            is_new = user is None or user.pk is None
            user = form.save()
            if is_new:
                messages.success(request, "Created!")
            else:
                messages.success(request, "Edited!")

            if can_list_users(request.user):
                return redirect("users-list")
            return redirect("users-home")
    else:
        form = UserForm(user=request.user, instance=user)

    return render(request, 'users/edit.html', {
        "form": form,
    })
