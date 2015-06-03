import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from functools import partial

import requests
from django.conf import settings
from django.db import transaction
from django.utils.timezone import now, utc

API_KEY = settings.ALMA_API_KEY

# these magical special values were derived from lots of trial and error
library_code = "AVS"
location_code = "OITAVS"
id_type = "UNIV_ID"


class AlmaError(Exception):
    """
    Wraps an error in the Alma api
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return json.dumps(self.value, indent=4, sort_keys=True)

    def __repr__(self):
        return str(self)


def default(obj):
    """
    Helper to handle datetime objects when converting an arbitrary
    datastructure to JSON
    """
    if isinstance(obj, datetime):
        return str(obj.astimezone(utc)).replace("+00:00", "Z").replace(" ", "T")

    raise TypeError("Type not serializable")


def request(endpoint, params=None, data=None, method="get"):
    """
    This is a low level wrapper for sending a request to Alma
    """
    if params is None:
        params = {}

    headers = {}
    params.update({
        "format": "json",
        "apikey": API_KEY
    })

    if method == "get":
        method = requests.get
    elif method in ["post", "delete"]:
        method = getattr(requests, method)
        headers['content-type'] = "application/json"
        if data:
            data = json.dumps(data, default=default)


    response = method("https://api-na.hosted.exlibrisgroup.com/" + endpoint, params=params, data=data, headers=headers)

    # no content to parse, but everything was successful
    if response.status_code == 204:
        return True

    try:
        content = json.loads(response.content.decode())
    except ValueError:
        print(response.content.decode())
        raise
    # wrap 4xx and 5xx status codes in an exception
    if 400 <= response.status_code < 600:
        raise AlmaError(content)

    return content


get = partial(request, method="get")
post = partial(request, method="post")
delete = partial(request, method="delete")


def get_users():
    """Get a list of users"""
    # TODO: Finish offset and limit stuff
    return get("almaws/v1/users", {"limit": 100, "offset": 0, "order_by": "primary_id"})


def get_user(identifer):
    return get('almaws/v1/users/' + str(identifer))


def get_libraries():
    return get("almaws/v1/conf/libraries")


def get_locations(library_code):
    return get("almaws/v1/conf/libraries/{0}/locations".format(library_code))


def get_codes(code):
    return get("almaws/v1/conf/code-tables/" + code)


def get_bib(mms_id):
    return get("almaws/v1/bibs/{mms_id}".format(mms_id=mms_id), params={"expand": "p_avail"})


def get_items():
    """
    Returns a list of dicts that represent items in Alma
    WARNING: This only gets the first 1000 rows from the report
    """
    data = {
        # See the following to understand where this magical path came from
        # https://developers.exlibrisgroup.com/blog/Working-with-Analytics-REST-APIs
        "path": "/shared/Portland State University/Reports/cg oit avs",
        "limit": 1000
    }

    # it takes a while for the report to run, so we poll every second to see if it's done
    while True:
        response = get("almaws/v1/analytics/reports", data)
        xml = ET.fromstring(response['anies'][0])
        if xml.findall("./IsFinished")[0].text == "false":
            data['token'] = xml.findall("./ResumptionToken")[0]
            time.sleep(1)
        else:
            break

    col_names = ["useless", "mms_id", "name", "library_code", "barcode", "description", "item_id", "category"]
    rows = []
    for i, row in enumerate(xml.findall(".//{urn:schemas-microsoft-com:xml-analysis:rowset}Row")):
        item = {}
        for col in row:
            # the tag name ends with a number (e.g. Column5), which we use to get the column
            # name
            col_index = int(col.tag[-1])
            item[col_names[col_index]] = col.text
        rows.append(item)

    return rows


def update_items():
    """
    Create and/or update all the Bibs and Items in the database so they match Alma
    """
    # TODO delete items that no longer exist?
    from alma.items.models import Item, Bib
    with transaction.atomic():
        for item in get_items():
            try:
                bib_obj = Bib.objects.get(pk=item['mms_id'])
            except Bib.DoesNotExist:
                bib_obj = Bib(pk=item['mms_id'])

            bib_obj.name = item['name']
            bib_obj.save()

            try:
                item_obj = Item.objects.get(pk=item['item_id'])
            except Item.DoesNotExist:
                item_obj = Item(pk=item['item_id'])

            col_names = ["mms_id", "barcode", "description", "category"]
            for col_name in col_names:
                try:
                    setattr(item_obj, col_name, item[col_name])
                except KeyError:
                    pass

            item_obj.bib = bib_obj
            item_obj.save()


def create_booking(username, mms_id, start_date, end_date):
    """
    Creates a booking by the user for the Bib with the specified mms_id, on the
    provided dates. The dates must be tz aware datetime objects
    """
    params = {
        "user_id": username,
        "user_id_type": id_type,
    }

    return post("almaws/v1/bibs/{mms_id}/requests".format(mms_id=mms_id), params=params, data={
        "request_type": "BOOKING",
        "pickup_location_type": "LIBRARY",
        "pickup_location_library": library_code,
        "booking_start_date": start_date,
        "booking_end_date": end_date,
    })


def delete_booking(request_id, mms_id):
    """
    Deletes a booking with the specified request_id for the mms_id. (Why you
    have to pass in the mms_id too is beyond me).
    """
    return delete("almaws/v1/bibs/{mms_id}/requests/{request_id}".format(request_id=request_id, mms_id=mms_id))


def get_availability(mms_id, days):
    """
    Returns the intervals of time the mms_id is not available, in the coming `days` days.
    """
    return get("almaws/v1/bibs/{mms_id}/booking-availability".format(mms_id=mms_id), {
        "period": days,
        "period_type": "days",
    })


def create_loan(username, barcode):
    """
    Creates a loan for the item with the specified barcode to `username`
    """
    params = {
        "user_id_type": id_type,
        "item_barcode": barcode
    }
    data = {
        "circ_desk": {"value": "DEFAULT_CIRC_DESK"},
        "library": {"value": library_code},
    }
    return post("almaws/v1/users/{user_id}/loans".format(user_id=username), params=params, data=data)


def return_loan(mms_id, item_id):
    """
    Checks in, un-loans, or returns (depending on your preferred terminology)
    an item with the specified mms_id and item_id
    """
    # we assume the first holding is where we want the item returned
    holding_id = get_holdings(mms_id)["holding"][0]["holding_id"]
    return scan_in(mms_id, holding_id, item_id)


def get_holdings(mms_id):
    return get("almaws/v1/bibs/{mms_id}/holdings".format(mms_id=mms_id))


def scan_in(mms_id, holding_id, item_id):
    """
    Performs a scan in operation
    """
    params = {
        "op": "scan",
        "library": library_code,
        "circ_desk": "DEFAULT_CIRC_DESK",
    }

    return post("almaws/v1/bibs/{mms_id}/holdings/{holding_id}/items/{item_id}".format(mms_id=mms_id, item_id=item_id, holding_id=holding_id), params=params)


def is_available(mms_id, intervals):
    """
    Yields True or False for every interval you pass in (True => available)

    `intervals` is assumed to be a list of two-tuples containing start and end
    datetime objects.
    """
    end = intervals[-1][1]
    days = (end - now()).days + 1
    response = get_availability(mms_id, days)
    # nothing got booked
    if response["booking_availability"] is None:
        response['booking_availability'] = []
    # O(n*m) algorithm since I'm worn out today
    for interval in intervals:
        for availability in response['booking_availability']:
            start = parse_alma_datetime(availability['from_time'])
            end = parse_alma_datetime(availability['to_time'])
            if start < interval[1] and end > interval[0]:
                yield False
                break
        else:
            yield True


def parse_alma_datetime(dt):
    """
    Converts an alma datetime string to an aware datetime object
    """
    try:
        dt = datetime.strptime(dt+"+0000", "%Y-%m-%dT%H:%M:%Sz%z")
    except ValueError:
        dt = datetime.strptime(dt+"+0000", "%Y-%m-%dT%H:%M:%S.%fz%z")

    return dt

#
# Some examples
#
#print(json.dumps(get_users(), indent=4))

#print(json.dumps(get_user("mdj2"), indent=4))
#print(json.dumps(get_codes("UserIdentifierTypes"), indent=4))
#print(json.dumps(create_booking("mdj2", "99902460728301853", "2015-06-05T10:10:10Z", "2015-06-05T11:10:10Z")))
#response = delete_booking("5497242890001853", 99902460736601853)
#if response != True:
#    print(json.dumps(response, indent=4))
#print(json.dumps(get_report("/shared/Portland State University/Reports/cg oit avs"), indent=4))
#update_items()
#print(json.dumps(create_loan("mdj2", "50110020840266"), indent=4))
# "99902462241301853"
#print(json.dumps(scan_in("99902462241301853", "22305518160001853", "23305517970001853"), indent=4))




# booking
#mms_id = "99902463600701853"
#print(json.dumps(create_booking("mdj2", mms_id, "2015-08-30T10:10:10Z", "2015-08-30T11:10:10Z"), indent=4))
#print(json.dumps(delete_booking("5640694860001853", "99902462241301853"), indent=4))
#print(json.dumps(get_availability(mms_id, 180), indent=4))
#print(is_available(mms_id, [(datetime(2015, 8, 29, 2, tzinfo=now().tzinfo), datetime(2015, 8, 29, 2, 59, tzinfo=now().tzinfo))]))
