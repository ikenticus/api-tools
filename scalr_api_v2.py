import base64
import datetime
import hashlib
import hmac
import json
import os
import pytz
import requests
import sys

from pprint import pprint

def scalr_request_authentication (key_id, key_secret, method, path, params, body,
        date=datetime.datetime.now(tz=pytz.timezone(os.environ.get("TZ", "UTC"))).isoformat()):
    return {
        'X-Scalr-Key-Id': key_id,
        'X-Scalr-Signature': scalr_signature_algorithm(key_secret, scalr_canonical_request(method, date, path, params, body)),
        'X-Scalr-Date': date,
        'X-Scalr-Debug': 1
    }

def scalr_signature_algorithm (key_secret, canon_req):
    return 'V1-HMAC-SHA256 %s' % base64.b64encode(hmac.new(str(key_secret), canon_req, hashlib.sha256).digest())

def scalr_canonical_request (method, date, path, params, body):
    return '\n'.join([method, date, path, params, body])

def scalr_api_call (creds, path, method='GET', params='', body=''):
    return requests.get(creds.get('api_url') + path,
                            headers = scalr_request_authentication(
                                creds.get('api_key_id'), creds.get('api_key_secret'), method, path, params, body
                            )
                        )

if __name__ == "__main__":
    config = sys.argv[0].replace('.py', '.json')
    creds = json.load(open(config))
    response = scalr_api_call(creds, '/api/v1beta0/account/environments')
    pprint(json.loads(response.content))
