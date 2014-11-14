import os
import sys
import cPickle
import hashlib
import requests
import webbrowser
from lxml import etree
from pprint import pprint
from datetime import datetime

from flickr_keys import *

FROBFILE = 'flickr.frob.cache'
PARENT = ' : '   # parent prefix
URL = {
    'auth': 'https://api.flickr.com/services/auth/',
    'rest': 'https://api.flickr.com/services/rest/',
    'upload': 'https://up.flickr.com/services/upload/',
}

def build_loop (xlist, parent=None):
    xdict = {}
    for node in xlist:
        title = node.xpath('@title')[0]
        if parent:
            title = title.replace(parent + PARENT, '')
        xdict[title] = {
            'id': node.xpath('@id')[0],
        }
        if len(node.xpath('collection')) > 0:
            xdict[title]['collection'] = build_loop(node.xpath('collection'))
        if len(node.xpath('set')) > 0:
            xdict[title]['album'] = build_loop(node.xpath('set'), parent=title)
    return xdict

def get_albums (auth):
    albums = []
    url = get_sig_url('%s?method=flickr.photosets.getList&user_id=%s&auth_token=%s' \
            % (URL.get('rest'), auth.get('user'), auth.get('token')))
    try:
        response = requests.get(url)
        contents = etree.fromstring(str(response.text))
        for album in contents.xpath('photosets/photoset'):
            albums.append({
                'id': album.xpath('@id')[0],
                'title': album.xpath('title/text()')[0],
            })
        #'url': '%s?method=flickr.photosets.getPhotos&photoset_id=' + id
        return albums
    except:
        raise Exception("Failed to retrieve albums")

def get_auth (frob, perms):
    url = get_sig_url('%s?frob=%s&perms=%s' % (URL.get('auth'), frob, perms))
    sys.stderr.write('\nOpen the following url in a browser and authorize it:\n%s\n\nThen click Enter/Return to continue...\n' % url)
    webbrowser.open_new(url)
    sys.stdin.readline()
    return get_token(frob)

def get_collections (auth):
    url = get_sig_url('%s?method=flickr.collections.getTree&user_id=%s&auth_token=%s' \
            % (URL.get('rest'), auth.get('user'), auth.get('token')))
    try:
        response = requests.get(url)
        contents = etree.fromstring(str(response.text))
        tree = build_loop(contents.xpath('collections/collection'))
        pprint(tree)
    except:
        raise Exception("Failed to retrieve collections")

def get_auth (frob, perms):
    url = get_sig_url('%s?frob=%s&perms=%s' % (URL.get('auth'), frob, perms))
    sys.stderr.write('\nOpen the following url in a browser and authorize it:\n%s\n\nThen click Enter/Return to continue...\n' % url)
def get_frob ():
    url = get_sig_url('%s?method=flickr.auth.getFrob' % URL.get('rest'))
    try:
        response = requests.get(url)
        contents = etree.fromstring(str(response.text))
        return contents.xpath('frob/text()')[0]
    except:
        raise Exception("Failed to retrieve frob")

def get_photos_from_album (auth, album=None):
    url = get_sig_url('%s?method=flickr.photosets.getPhotos&user_id=%s&auth_token=%s&photoset_id=%s' \
            % (URL.get('rest'), auth.get('user'), auth.get('token'), album))

def get_photos_orphaned (auth):
    url = get_sig_url('%s?method=flickr.photos.getNotInSet&user_id=%s&auth_token=%s' \
            % (URL.get('rest'), auth.get('user'), auth.get('token')))

def get_sig_url (url):
    url += "&api_key=" + APIKEY
    params = sorted(url.split('?')[1].split('&'))
    params = ''.join([ p.replace('=', '') for p in params ])
    sign = hashlib.md5(SECRET + params).hexdigest()
    return url + "&api_sig=" + sign
    
def get_token (frob):
    url = get_sig_url('%s?method=flickr.auth.getToken&frob=%s' % (URL.get('rest'), frob))
    try:
        response = requests.get(url)
        contents = etree.fromstring(str(response.text))
        token = str(contents.xpath('auth/token/text()')[0])
        user = str(contents.xpath('auth/user/@nsid')[0])
        return user, token
    except:
        raise Exception("Failed to retrieve token")


if __name__ == '__main__':
    today = str(datetime.now().strftime('%D %r'))
    try:
        cache = open(FROBFILE, 'r')
        auth = cPickle.load(cache)
        cache.close()
    except:
        (user, token) = get_auth(get_frob(), 'read')
        auth = { 'user': user, 'token': token, 'date': today }  
        cache = open(FROBFILE, 'w')
        cPickle.dump(auth, cache)
        cache.close()

    get_collections(auth)
