'''
    Name:   flickr_oauth_tool
    Author: ikenticus
    Date:   2014/11/18
    Notes:  Using flickr oauth to upload/download photo collection
            maintaining local directory structure based on:
            * https://www.flickr.com/services/api/auth.oauth.html

            Referenced these documents for some additional direction:
            * http://mkelsey.com/2011/07/03/Flickr-oAuth-Python-Example/
            * http://snakeycode.wordpress.com/2013/05/01/troubles-with-the-flickr-api/
'''

import os
import sys
import json
import time
import oauth2
import cPickle
import requests
import webbrowser
from pprint import pprint
from datetime import datetime

from flickr_keys import *

CACHEFILE = 'flickr.oauth.cache'
DUMMYJPG = '1x1.jpg'
ROOTDIR = 'photos'  # default photo dir
PERPAGE = 100       # photos per album page
PARENT = ' : '      # parent prefix
URL = {
    'auth': 'https://api.flickr.com/services/auth/',
    'rest': 'https://api.flickr.com/services/rest/',
    'upload': 'https://up.flickr.com/services/upload/',
    'oauth': 'http://www.flickr.com/services/oauth/',
    'callback': 'http://www.usatoday.com/',
}

def oauth_access_token ():
    return

def oauth_authorize (auth, perms):
    url = '%sauthorize?oauth_token=%s&perms=%s' % (URL.get('oauth'), auth.get('oauth_token'), perms)
    sys.stdout.write('\nOpen the following url in a browser and authorize it:\n%s\n\nThen Enter oauth_verifier and press Return to continue...\n' % url)
    webbrowser.open_new(url)
    return sys.stdin.readline().rstrip()

def oauth_request (method='GET', action=True, auth={}, url=None):
    token = None
    consumer = oauth2.Consumer(key=APIKEY,secret=SECRET)
    params = {
        'oauth_version': "1.0",
        'oauth_nonce': oauth2.generate_nonce(),
        'oauth_timestamp': int(time.time()),
        'oauth_consumer_key': consumer.key,
    }

    if auth:
        token = oauth2.Token(auth.get('oauth_token'), auth.get('oauth_token_secret'))
        params['oauth_token'] = token.key
        if auth.get('oauth_verifier'):
            params['oauth_verifier']  = auth.get('oauth_verifier')
            token.set_verifier(auth.get('oauth_verifier'))
            url = URL.get('oauth') + 'access_token'
    else:
        url = URL.get('oauth') + 'request_token'
        params['oauth_callback'] = URL.get('callback')

    if url:
        request = oauth2.Request(method=method, url=url, parameters=params)
        request.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), consumer, token)
        if action:
            response = requests.get(request.to_url())
            return response.text
        else:
            return request
    else:
        return

def split_url_to_dict (query):
    udict = {}
    for param in query.split('&'):
        kv = param.split('=')
        udict[kv[0]] = kv[1]
    return udict

def upload_dummy_photo (auth):
    #url = '%s?photo=%s' % (URL.get('upload'), DUMMYJPG)
    url = URL.get('upload')
    files = {'photo': open(DUMMYJPG, 'rb')}
    request = oauth_request(action=False, auth=auth, method='POST', url=url)
    response = requests.post(url, data=request, files=files)
    print response.status_code
    print response.text


if __name__ == '__main__':
    today = str(datetime.now().strftime('%D %r'))

    #if len(sys.argv) < 2:
    #    usage()

    try:
        cache = open(CACHEFILE, 'r')
        auth = cPickle.load(cache)
        cache.close()
    except:
        auth = split_url_to_dict(oauth_request())
        auth['oauth_verifier'] = oauth_authorize(auth, 'write')

        auth = split_url_to_dict(oauth_request(auth=auth))
        auth['date'] = today

        cache = open(CACHEFILE, 'w')
        cPickle.dump(auth, cache)
        cache.close()

    upload_dummy_photo(auth)

