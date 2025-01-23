import requests
import json
import logging


from tenacity import retry, wait_random_exponential, stop_after_attempt

from settings import WEBSERVICE_URL


@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
def send_request(data) -> bool | dict:
    datajson = json.dumps(data)
    r = requests.post( WEBSERVICE_URL, data=datajson)
    print(r)
    if r.status_code == 200:
        response = r.json()
        return response
    else:
        logging.error(f"Error {r.status_code} al intentar realizar la petición al web service {WEBSERVICE_URL}")
        raise Exception(f"Error {r.status_code} al intentar realizar la petición al web service {WEBSERVICE_URL}")
    