from arcutils import will_be_deleted_with
from arcutils.ldap import escape, ldapsearch, parse_profile
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import UserForm
from .models import User
from .perms import can_list_users, permissions


@login_required
def autocomplete(request):
    """
    Does an LDAP search and returns a JSON array of objects
    """
    q = escape(request.GET.get('query', ""))
    if len(q) < 3:
        return JsonResponse([], safe=False)

    # only return a handful of results
    MAX_RESULTS = 5

    search = '(uid={q}*)'.format(q=q)
    results = ldapsearch(search, size_limit=MAX_RESULTS)
    # I don't think LDAP guarantees the sort order, so we have to sort ourselves
    results.sort(key=lambda o: o[1]['uid'][0])
    output = []

    for result in results[:MAX_RESULTS]:
        output.append(parse_profile(result[1]))

    return JsonResponse(output, safe=False)
