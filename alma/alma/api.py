import requests
import json
from functools import partial

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

    params.update({
        "format": "json",
        "apikey": API_KEY
    })

    if method == "get":
        method = requests.get
    elif method == "post":
        method = requests.post

    response = method("https://api-na.hosted.exlibrisgroup.com/" + endpoint, params=params, data=data)

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

library_code = "AVS"
location_code = "OITAVS"
id_type = "UNIV_ID"

def create_booking(username, barcode, start_date, end_date):
    params = {
        "item_barcode": barcode,
        #"user_id_type": id_type,
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

print(json.dumps(get_users(), indent=4))

#print(json.dumps(get_user("mdj2"), indent=4))
#print(json.dumps(get_codes("UserIdentifierTypes"), indent=4))
print(json.dumps(create_booking("200035", 123, "2015-05-05T10:10:10Z", "2015-05-05T11:10:10Z")))
