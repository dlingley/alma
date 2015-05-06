import requests
import json
import time
from functools import partial
import xml.etree.ElementTree as ET
#from alma.items.models import Item

API_KEY = "l7xx12b2a3ae884d4b48a5de50b3f8539fa6"

class AlmaError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return json.dumps(self.value, indent=4, sort_keys=True)

    def __repr__(self):
        return str(self)


def request(endpoint, params=None, data=None, method="get"):
    if params is None:
        params = {}

    headers = {}
    params.update({
        "format": "json",
        "apikey": API_KEY
    })

    if method == "get":
        method = requests.get
    elif method == "post":
        method = requests.post
        headers['content-type'] = "application/json"
        if data:
            data = json.dumps(data)


    response = method("https://api-na.hosted.exlibrisgroup.com/" + endpoint, params=params, data=data, headers=headers)

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


def get_users():
    return get("almaws/v1/users", {"limit": 100, "offset": 0, "order_by": "primary_id"})


def get_user(identifer):
    return get('almaws/v1/users/' + str(identifer))


def get_libraries():
    return get("almaws/v1/conf/libraries")


def get_locations(library_code):
    return get("almaws/v1/conf/libraries/{0}/locations".format(library_code))


def get_codes(code):
    return get("almaws/v1/conf/code-tables/" + code)


def get_items():
    """
    Returns a list of dicts that represent items in Alma
    WARNING: This only gets the first 1000 rows from the report
    """
    data = {
        "path": "/shared/Portland State University/Reports/cg oit avs",
        "limit": 1000
    }

    while True:
        response = get("almaws/v1/analytics/reports", data)
        xml = ET.fromstring(response['anies'][0])
        if xml.findall("./IsFinished")[0].text == "false":
            data['token'] = xml.findall("./ResumptionToken")[0]
            time.sleep(1)
        else:
            break

    #xml = ET.fromstring(open("xml.txt", "r").read())
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
    for item in get_items():
        try:
            model_obj = Item.objects.get(pk=item['item_id'])
        except Item.DoesNotExist:
            model_obj = Item(pk=item['item_id'])

        col_names = ["mms_id", "name", "library_code", "barcode", "description", "category"]
        for col_name in col_names:
            try:
                setattr(model_obj, col_name, item[col_name])
            except KeyError:
                pass

        model_obj.save()


library_code = "AVS"
location_code = "OITAVS"
id_type = "UNIV_ID"

def create_booking(username, item_id, start_date, end_date):
    params = {
        "item_pid": item_id,
        "user_id_type": id_type,
    }

    return post("almaws/v1/users/%s/requests" % username, params=params, data={
        "request_type": "BOOKING",
        "pickup_location_type": "LIBRARY",
        "pickup_location_library": library_code,
        "booking_start_date": start_date,
        "booking_end_date": end_date,
    })
#
#{
#    "item_pid": 123, # or
#    "item_barcode": 123,
#    "user_id_type": id_type
#{
#    "request_type": "BOOKING",
#    "pickup_location_type": "LIBRARY",
#    "pickup_location_library": library_code,
#    "booking_start_date": now(),
#    "booking_end_date": now(),
#}

#print(json.dumps(get_users(), indent=4))

#print(json.dumps(get_user("mdj2"), indent=4))
#print(json.dumps(get_codes("UserIdentifierTypes"), indent=4))
#print(json.dumps(create_booking("200035", 123, "2015-05-05T10:10:10Z", "2015-05-05T11:10:10Z")))
#print(json.dumps(get_report("/shared/Portland State University/Reports/cg oit avs"), indent=4))
print(json.dumps(create_booking("mdj2", "23305517810001853", "2015-05-06T10:10:10Z", "2015-05-06T11:10:10Z")))
