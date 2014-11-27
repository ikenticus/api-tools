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
import inspect
import requests
import webbrowser
from lxml import etree
from pprint import pprint
from datetime import datetime

from flickr_keys import *

CACHEFILE = 'flickr.oauth.cache'
DUMMYIMG = 'dummy.jpg'
ROOTDIR = 'photos'  # default photo dir
PERPAGE = 100       # photos per album page
PARENT = ' : '      # parent prefix
URL = {
    'auth': 'https://api.flickr.com/services/auth/',
    'rest': 'https://api.flickr.com/services/rest/',
    'upload': 'https://up.flickr.com/services/upload/',
    'oauth': 'http://www.flickr.com/services/oauth/',
    'callback': 'http://www.flickr.com/',
}

def action_download (auth, args):
    rootdir = args[0] if len(args) > 0 else ROOTDIR
    download_collections (auth, get_collections(auth), rootdir)

def action_upload (auth, args):
    print 'UPLOAD'
    return
    rootdir = args[0] if len(args) > 0 else ROOTDIR
    online = get_collections(auth)
    # check dummy photo
    upload_directories (auth, online, rootdir)

def action_view (auth, args):
    pprint(get_collections(auth))

def check_oauth_token (auth):
    url = '%s?method=flickr.auth.oauth.checkToken' % URL.get('rest')
    flickr_request(auth, url)

def download_album (auth, id, rootdir):
    photos = get_album_photos(auth, id)
    for photo in photos:
        filename = '%s/%s.jpg' % (rootdir, photo.get('title').lower())
        if os.path.exists(filename):
            sys.stderr.write('Skipping download, already exists: %s\n' % filename)
        else:
            download_photo(auth, photo.get('id'), filename)

def download_albums (auth, albums, rootdir):
    for album in albums.keys():
        photodir = rootdir + '/' + album
        if not os.path.exists(photodir):
            os.makedirs(photodir)
        id = albums.get(album).get('id')
        download_album(auth, id, photodir)

def download_collections (auth, collections, rootdir):
    for collection in collections.keys():
        photodir = rootdir + '/' + collection
        if not os.path.exists(photodir):
            os.makedirs(photodir)
        sub = collections.get(collection)
        if sub.get('collection'):
            download_collections(auth, sub.get('collection'), photodir)
        elif sub.get('album'):
            download_albums(auth, sub.get('album'), photodir)

def download_photo (auth, id, filename):
    photo = get_photo(auth, id)
    try:
        response = requests.get(photo.get('source'), stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
        sys.stdout.write('Downloaded %s: %s\n' % (photo.get('label'), filename))
    except:
        sys.stdout.write('Failed to get %s: %s\n' % (photo.get('label'), filename))
        raise Exception('Failed to download photo')

def flickr_request (auth, url):
    caller = inspect.getouterframes(inspect.currentframe(), 2)[1][3].replace('_', ' ')
    sys.stdout.write('Attempting to %s\n' % caller)
    try:
        url += '&api_key=%s' % APIKEY
        request = oauth_request(action=False, auth=auth, method='GET', url=url)
        url += '&' + '&'.join([ '%s=%s' % (x, request[x]) for x in request.keys() ])
        response = requests.get(url, data=request)
        return etree.fromstring(str(response.text))
    except:
        raise Exception('Failed to %s' % caller)

def get_album_photos (auth, albumid, perpage=PERPAGE, page=1, photos=[]):
    url = '%s?method=flickr.photosets.getPhotos&photoset_id=%s&page=%s&per_page=%s' \
            % (URL.get('rest'), albumid, page, perpage)
    contents = flickr_request(auth, url)
    for photo in contents.xpath('photoset/photo'):
        photos.append({
            'id': photo.xpath('@id')[0],
            'title': photo.xpath('@title')[0],
        })
    pages = int(contents.xpath('photoset/@pages')[0])
    if page < pages:
        photos = get_album_photos(auth, albumid, page=page+1, photos=photos)
    return photos

def get_albums (auth):
    albums = []
    url = '%s?method=flickr.photosets.getList' % URL.get('rest')
    contents = flickr_request(auth, url)
    for album in contents.xpath('photosets/photoset'):
        albums.append({
            'id': album.xpath('@id')[0],
            'title': album.xpath('title/text()')[0],
        })
    return albums

def get_collections (auth):
    url = '%s?method=flickr.collections.getTree' % URL.get('rest')
    contents = flickr_request(auth, url)
    return loop_collection(contents.xpath('collections/collection'))

def get_orphaned_photos (auth):
    url = '%s?method=flickr.photos.getNotInSet' % URL.get('rest')

def get_photo (auth, id):
    url = '%s?method=flickr.photos.getSizes&photo_id=%s' % (URL.get('rest'), id)
    contents = flickr_request(auth, url)
    largest = contents.xpath('sizes/size')[-1]
    photo = {
        'label': largest.xpath('@label')[0],
        'source': largest.xpath('@source')[0],
    }
    return photo

def loop_collection (xlist, parent=None):
    xdict = {}
    for node in xlist:
        title = node.xpath('@title')[0]
        if parent:
            title = title.replace(parent + PARENT, '')
        xdict[title] = {
            'id': node.xpath('@id')[0],
        }
        if len(node.xpath('collection')) > 0:
            xdict[title]['collection'] = loop_collection(node.xpath('collection'))
        if len(node.xpath('set')) > 0:
            xdict[title]['album'] = loop_collection(node.xpath('set'), parent=title)
    return xdict

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

def search_photos (auth):
    url = '%s?method=flickr.photos.search' % URL.get('rest')
    request = oauth_request(action=False, auth=auth, method='POST', url=url)
    response = requests.post(url, data=request, headers=headers, files=files)
    contents = etree.fromstring(str(response.text))

def split_url_to_dict (query):
    udict = {}
    for param in query.split('&'):
        kv = param.split('=')
        udict[kv[0]] = kv[1]
    return udict

def upload_dummy_photo (auth):
    url = URL.get('upload')
    files = {'photo': open(DUMMYIMG, 'rb')}
    request = oauth_request(action=False, auth=auth, method='POST', url=url)
    response = requests.post(url, data=request, files=files)
    contents = etree.fromstring(str(response.text))
    return contents.xpath('photoid/text()')[0]

def usage():
    print """Usage: %s action [rootdir:photos]

    actions: %s
""" % (
        os.path.basename(sys.argv[0]),
        ', '.join(ACTIONS.keys()),
        )
    sys.exit(0)


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
        auth.update({
            'date': today,
            'dummy': str(upload_dummy_photo(auth)),
        })

        cache = open(CACHEFILE, 'w')
        cPickle.dump(auth, cache)
        cache.close()

    ACTIONS = { a.split('_')[1]:getattr(sys.modules[__name__], a)
                for a in dir(sys.modules[__name__])
                if a.startswith('action_') }

    print auth
    try:
        action = sys.argv[1]
        ACTIONS[action](auth, sys.argv[2:])
    except:
        usage()
