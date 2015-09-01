from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from elasticsearch_dsl import Q

from .indexes import BibIndex, ItemIndex


@login_required
def autocomplete(request):
    """
    Searches the for items that match the user's input on the barcode field,
    and combines that with the results of searching the Bib index for matches
    on any field.

    The reason we only match on an Item's barcode is that the only time we want
    to see an Item in the results is if a barcode is entered (which means the
    Item is being checked-in or checked-out).

    We want to match on a Bib's name, because the user will want to type
    something in like "Firewire cable" and create a reservation for the Bib.
    """
    query = request.GET.get("query", "")

    # first, find any matches on the Item index just using the barcode field
    dsl = Q("multi_match", analyzer="standard", query=query, fields=["barcode"])
    dsl = ItemIndex.objects.query(dsl)
    items = []
    for result in dsl.execute():
        items.append({
            "barcode": result.barcode,
            "name": result.name,
            "description": result.description,
            "category": result.category,
            "type": "ITEM",
        })

    # second, we query for matching Bibs
    dsl = Q("multi_match", query=query, fields=["name"])
    # on the typeahead autocomplete textbox, in the user interface, if the user selects an item,
    # that could potentially re-order the items in the typeahead drop down
    # (because ES will re-query based on the text of the option they selected). That
    # causes some weird issues when using the TAB key in that form field. To
    # avoid that problem, we boost the item_id field, so once it is selected,
    # it will always appear first in the search results.
    dsl |= Q("multi_match", analyzer="standard", query=query, fields=["mms_id^10"])
    dsl = BibIndex.objects.query(dsl)
    for result in dsl.execute():
        items.append({
            "mms_id": result.mms_id,
            "name": result.name,
            "type": "BIB",
        })

    return JsonResponse(items, safe=False)
