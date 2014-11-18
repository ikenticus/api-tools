'''
    Name:   flickr_oauth_tool
    Author: ikenticus
    Date:   2014/11/18
    Notes:  Using flickr oauth to upload/download photo collection
            maintaining local directory structure
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

def oauth_get_token (auth={}, url=None):
    token = None
    params = {
        'oauth_version': "1.0",
        'oauth_nonce': oauth2.generate_nonce(),
        'oauth_timestamp': int(time.time()),
    }

    if auth:
        params['oauth_token'] = auth.get('oauth_token')
        token = oauth2.Token(auth['oauth_token'], auth['oauth_token_secret'])
        if auth.get('oauth_verifier'):
            params['oauth_verifier']  = auth.get('oauth_verifier')
            token.set_verifier(auth.get('oauth_verifier'))
            url = URL.get('oauth') + 'access_token'
    else:
        url = URL.get('oauth') + 'request_token'
        params['oauth_callback'] = URL.get('callback')

    if url:
        consumer = oauth2.Consumer(key=APIKEY,secret=SECRET)
        params['oauth_consumer_key'] = consumer.key
        request = oauth2.Request(method='GET', url=url, parameters=params)
        request.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), consumer, token)
        response = requests.get(request.to_url())
        return split_url_to_dict(response.text)
    else:
        return

def split_url_to_dict (query):
    udict = {}
    for param in query.split('&'):
        kv = param.split('=')
        udict[kv[0]] = kv[1]
    return udict


if __name__ == '__main__':
    today = str(datetime.now().strftime('%D %r'))

    #if len(sys.argv) < 2:
    #    usage()

    try:
        cache = open(CACHEFILE, 'r')
        auth = cPickle.load(cache)
        cache.close()
    except:
        auth = oauth_get_token()
        auth['oauth_verifier'] = oauth_authorize(auth, 'write')
        auth = oauth_get_token(auth) 
        auth['date'] = today
        cache = open(CACHEFILE, 'w')
        cPickle.dump(auth, cache)
        cache.close()

    print auth
#http://mkelsey.com/2011/07/03/Flickr-oAuth-Python-Example/
#http://snakeycode.wordpress.com/2013/05/01/troubles-with-the-flickr-api/
