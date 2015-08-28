from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from elasticsearch_dsl import Q

from .indexes import BibIndex, ItemIndex


@login_required
def autocomplete(request):
    """
    Searches all the fields on the Item index and returns the results
    """
    query = request.GET.get("query", "")
    dsl = Q("multi_match", query=query, fields=["description", "category", "name", "barcode"])
    # on the typeahead autocomplete textbox, in the user interface, if the user selects an item,
    # that could potentially re-order the items in the typeahead drop down
    # (because ES will re-query based on the text of the option they selected). That
    # causes some weird issues when using the TAB key in that form field. To
    # avoid that problem, we boost the item_id field, so once it is selected,
    # it will always appear first in the search results.
    dsl |= Q("multi_match", analyzer="standard", query=query, fields=["item_id^10"])
    dsl = ItemIndex.objects.query(dsl)
    items = []
    for result in dsl.execute():
        items.append({
            "barcode": result.barcode,
            "name": result.name,
            "description": result.description,
            "category": result.category,
        })

    return JsonResponse(items, safe=False)

@login_required
def autocomplete_bibs(request):
    """
    Searches all the fields on the Bib index and returns the results
    """
    query = request.GET.get("query", "")
    dsl = Q("multi_match", query=query, fields=["name"])
    # on the typeahead autocomplete textbox, in the user interface, if the user selects an item,
    # that could potentially re-order the items in the typeahead drop down
    # (because ES will re-query based on the text of the option they selected). That
    # causes some weird issues when using the TAB key in that form field. To
    # avoid that problem, we boost the item_id field, so once it is selected,
    # it will always appear first in the search results.
    dsl |= Q("multi_match", analyzer="standard", query=query, fields=["mms_id^10"])
    dsl = BibIndex.objects.query(dsl)
    items = []
    for result in dsl.execute():
        items.append({
            "mms_id": result.mms_id,
            "name": result.name,
        })

    return JsonResponse(items, safe=False)
