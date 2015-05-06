from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Item


@login_required
def autocomplete(request):
    """
    Searches all the fields on the Item index and returns the results
    """
    query = request.GET.get("query", "")
    query = Item.search.query("multi_match", query=query, fields=[field.name for field in Item.search.fields])
    items = []
    for result in query.execute():
        items.append({
            "item_id": result.item_id,
            "name": result.name,
            "description": result.description,
            "category": result.category,
        })

    return JsonResponse(items, safe=False)
