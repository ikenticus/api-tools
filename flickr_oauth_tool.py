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

            Seems that flickr API constantly times out, need to retry everything
'''

import os
import re
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

DEBUG = False
SINGLE = False
MAXRETRIES = 50
CACHEFILE = 'flickr.oauth.cache'
DUMMYIMG = 'dummy.jpg'
ROOTDIR = 'photos'  # default photo dir
PERPAGE = 100       # photos per album page
PARENT = ' : '      # parent prefix
VALIDEXT = ['.gif', '.jpg', 'jpeg', '.png']
URL = {
    'auth': 'https://api.flickr.com/services/auth/',
    'rest': 'https://api.flickr.com/services/rest/',
    'upload': 'https://up.flickr.com/services/upload/',
    'oauth': 'http://www.flickr.com/services/oauth/',
    'callback': 'http://www.flickr.com/',
}

def action_cleanup (auth, args):
    cleanup_orphan_photos(auth)
    #get_photo_perms(auth, auth.get('dummy'))   # ispublic isfriend isfamily permcomment permaddmeta

def action_download (auth, args):
    rootdir = args[0] if len(args) > 0 else ROOTDIR
    download_collections (auth, get_collections(auth), rootdir)

def action_upload (auth, args):
    rootdir = args[0] if len(args) > 0 else ROOTDIR
    online = get_collections(auth)
    online = upload_directories (auth, online, rootdir)
    if DEBUG:
        pprint(online)
    cleanup_widow_albums(online)

def action_view (auth, args):
    pprint(get_collections(auth))

def add_album_photo (auth, album, photo):
    url = '%s?method=flickr.photosets.addPhoto&photoset_id=%s&photo_id=%s' \
            % (URL.get('rest'), album, photo)
    return flickr_request(auth, url)

def check_oauth_token (auth):
    url = '%s?method=flickr.auth.oauth.checkToken' % URL.get('rest')
    flickr_request(auth, url)

def check_debug (args):
    global DEBUG, SINGLE
    for arg in args:
        if arg == 'debug':
            DEBUG = True
        if arg == 'single':
            SINGLE = True

def check_image_files (images):
    return [ x for x in images if x[-4:].lower() in VALIDEXT ]

def check_make_dir (path):
    if not os.path.exists(path):
        os.makedirs(path)

def cleanup_orphan_photos (auth):
    photos = get_orphaned_photos(auth)
    #pprint(photos)
    for photo in photos:
        delete_photo(auth, photo.get('id'))

def cleanup_widow_albums (tree):
    sys.stdout.write('Removing widow albums that only contain dummy photo...\n')
    for year in tree.keys():
        if year == 'album':
            continue
        for month in tree.get(year).get('collection'):
            yrmo = tree.get(year).get('collection').get(month)
            if 'album' in yrmo.keys():
                for album in yrmo.get('album'):
                    photoset = yrmo.get('album').get(album)
                    photos = photoset.get('photos')
                    if not photos:
                        continue
                    if photos and len(photos) == 1 and 'dummy' in photos:
                        sys.stdout.write('Delete %s/%s/%s\n' % (year, month, album))
                        if DEBUG:
                            print year, month, album, photos
                        else:
                            delete_album(auth, photoset.get('id'))

def create_album (auth, cdict, title):
    url = '%s?method=flickr.photosets.create&title=%s&primary_photo_id=%s' \
            % (URL.get('rest'), title, auth.get('dummy'))
    contents = flickr_request(auth, url)
    cdict[title] = { 'id': contents.xpath('photoset/@id')[0] }
    return cdict

def create_collection (auth, cdict, title, parent):
    url = '%s?method=flickr.collections.create&title=%s&parent_id=%s' \
            % (URL.get('rest'), title, parent)
    contents = flickr_request(auth, url)
    cdict[title] = { 'id': contents.xpath('collection/@id')[0] }
    return cdict

def create_sub_collection (auth, tree, root, name):
    sub = tree.get(root)
    if not sub.get('collection'):
        sub['collection'] = {}
    if not sub.get('collection').get(name):
        sub['collection'] = create_collection (auth, sub['collection'], name, sub.get('id'))
    return tree

def delete_album (auth, album):
    url = '%s?method=flickr.photosets.delete&photoset_id=%s' \
            % (URL.get('rest'), album)
    return flickr_request(auth, url)

def delete_photo (auth, photo):
    url = '%s?method=flickr.photos.delete&photo_id=%s' \
            % (URL.get('rest'), photo)
    return flickr_request(auth, url)

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
        check_make_dir(photodir)
        id = albums.get(album).get('id')
        download_album(auth, id, photodir)

def download_collections (auth, collections, rootdir):
    for collection in collections.keys():
        photodir = rootdir + '/' + collection
        check_make_dir(photodir)
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
        sys.stderr.write('Failed to get %s: %s\n' % (photo.get('label'), filename))
        raise Exception('Failed to download photo')

def edit_collection_albums (auth, tree):
    albums = tree.get('album')
    photosets = ','.join([ albums.get(x).get('id') for x in albums.keys() ])
    collection = tree.get('id')
    url = '%s?method=flickr.collections.editSets&collection_id=%s&photoset_ids=%s' \
            % (URL.get('rest'), collection, photosets)
    return flickr_request(auth, url)

def flickr_request (auth, url):
    params = url.split('&')[1:]
    try:
        title = [ x for x in params if x.startswith('title=') ][0].split('=')[1]
    except:
        title = ','.join([ x for x in params if '_id=' in x ])
    if title.endswith(auth.get('dummy')):
        title = 'dummy'
    caller = inspect.getouterframes(inspect.currentframe(), 2)[1][3].replace('_', ' ')
    sys.stdout.write('[%s] Attempting to %s %s\n' % (datetime.now().strftime('%T'), caller, title))
    url += '&api_key=%s' % APIKEY
    attempt = 1
    complete = False
    while not complete and attempt < MAXRETRIES:
        try:
            request = oauth_request(action=False, auth=auth, method='GET', url=url)
            nurl = '%s&%s' % (url, '&'.join([ '%s=%s' % (x, request[x]) for x in request.keys() ]))
            response = requests.get(nurl, data=request)
            if response.status_code == 200:
                #print response.text
                xml = etree.fromstring(str(response.text))
                if xml.xpath('err/@code'):
                    sys.stderr.write('Error %s: %s\n' % (xml.xpath('err/@code')[0], xml.xpath('err/@msg')[0]))
                return xml
                complete = True
        except IOError as e:
            sys.stderr.write('...failed to %s attempt %d: %s\n' % (caller, attempt, e))
        attempt = attempt + 1
    raise Exception('Failed to %s after %d attempts' % (caller, MAXRETRIES))

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
    online = loop_collection(contents.xpath('collections/collection'))
    online = get_orphaned_albums(auth, online)
    return online

def get_nested(dct, *keys, **kwargs):
    current = dct
    default = kwargs.get("default")
    used = []

    for key in keys:
        if isinstance(current, dict):
            try:
                current = current[key]
            except KeyError:
                return default
        elif isinstance(current, list):
            try:
                current = current[key]
            except IndexError:
                return default
        elif current is None:
            return default
        else:
            raise ValueError('The value %r at %r is not a dict or list'
                             % (current, '.'.join(used)))
        if current is None:
            return default
        used.append(key)
    return current

def get_orphaned_albums (auth, collections):
    orphans = { x.get('title'): {'id': x.get('id')} for x in get_albums(auth) if '-' not in x.get('title') }
    collections['album'] = orphans
    return collections

def get_orphaned_photos (auth, perpage=PERPAGE, page=1, photos=[]):
    url = '%s?method=flickr.photos.getNotInSet&page=%s&per_page=%s' \
            % (URL.get('rest'), page, perpage)
    contents = flickr_request(auth, url)
    for photo in contents.xpath('photos/photo'):
        if photo.xpath('@id')[0] != auth.get('dummy'):
            photos.append({
                'id': photo.xpath('@id')[0],
                'title': photo.xpath('@title')[0],
            })
    pages = int(contents.xpath('photos/@pages')[0])
    total = int(contents.xpath('photos/@total')[0])
    if page < pages:
        sys.stdout.write('Retrieving page %d of %d of %d orphaned photos\n' % (page, pages, total))
        photos = get_orphaned_photos(auth, page=page+1, photos=photos)
    return photos

def get_photo (auth, id):
    url = '%s?method=flickr.photos.getSizes&photo_id=%s' % (URL.get('rest'), id)
    contents = flickr_request(auth, url)
    largest = contents.xpath('sizes/size')[-1]
    photo = {
        'label': largest.xpath('@label')[0],
        'source': largest.xpath('@source')[0],
    }
    return photo

def get_photo_perms (auth, photo):
    url = '%s?method=flickr.photos.getPerms&photo_id=%s' % (URL.get('rest'), photo)
    contents = flickr_request(auth, url)
    return contents.xpath('perms')[0].attrib

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

def remove_album_photo (auth, album, photo):
    url = '%s?method=flickr.photosets.removePhoto&photoset_id=%s&photo_id=%s' \
            % (URL.get('rest'), album, photo)
    return flickr_request(auth, url)

def remove_collection_album (auth, collection, album):
    url = '%s?method=flickr.collections.removeSet&collection_id=%s&photoset_id=%s' \
            % (URL.get('rest'), collection, album)
    return flickr_request(auth, url)

def search_photos (auth):
    url = '%s?method=flickr.photos.search' % URL.get('rest')
    request = oauth_request(action=False, auth=auth, method='POST', url=url)
    response = requests.post(url, data=request, headers=headers, files=files)
    contents = etree.fromstring(str(response.text))

def set_album_photo (auth, album, photo):
    url = '%s?method=flickr.photosets.setPrimaryPhoto&photoset_id=%s&photo_id=%s' \
            % (URL.get('rest'), album, photo)
    return flickr_request(auth, url)

def set_photo_perms (auth, photo):
    url = '%s?method=flickr.photos.setPerms&photo_id=%s' \
            % (URL.get('rest'), photo) + \
            '&is_public=0&is_friend=1&is_family=1&perm_comment=1&perm_addmeta=1'
    return flickr_request(auth, url)

def split_url_to_dict (query):
    udict = {}
    for param in query.split('&'):
        kv = param.split('=')
        udict[kv[0]] = kv[1]
    return udict

def upload_collection_album (auth, tree, root, name):
    # add dummy photo to create new album
    album = re.sub('^:', '', '%s:%s' % (':'.join(root.split('/')[2:]), name))
    parent = root.split('/')[:2]
    if len(parent) == 1:
        # root album not part of the yyyy/yyyymm collections
        sub = tree
    else:
        parent.insert(1, 'collection')
        sub = get_nested(tree, *parent)
    if not sub.get('album'):
        sub['album'] = {}
    if not sub.get('album').get(album):
        sub['album'] = create_album(auth, sub['album'], album)
        edit_collection_albums(auth, sub)
    photoset = sub['album'][album]
    photoset['photos'] = [ x.get('title') for x in get_album_photos(auth, photoset.get('id'), photos=[]) ]
    return tree

def upload_directories (auth, online, rootdir):
    for root, dnames, fnames in os.walk(rootdir, followlinks=True):
        if 'offline' in root or root.endswith('.Thumbnails'):
            continue
        croot = root.replace(rootdir + '/', '')
        for dname in dnames:
            if dname.endswith('offline') or dname.endswith('.Thumbnails'):
                continue
            if root == rootdir and dname.startswith('20'):
                if not online.get(dname):
                    online = create_collection(auth, online, dname, 0)
            elif dname.startswith(os.path.basename(root)):
                online = create_sub_collection(auth, online, croot, dname)
            else:
                online = upload_collection_album(auth, online, croot, dname)
        files = check_image_files(fnames)
        if files:
            online = upload_album_photos(auth, online, croot, root, files)
    sys.stdout.write('Upload complete\n%s\n' % ('=' * 75))
    return online

def upload_album_photos (auth, tree, root, dir, files):
    parent = root.split('/')[:2]
    if parent[-1] == root.split('/')[-1]:
        sys.stderr.write('Unsorted photos found in %s, please correctly place them in a subdir to continue.\n' % root)
        sys.exit(3)
    if len(parent) == 1:
        parent.insert(0, 'album')
    else:
        parent.insert(1, 'collection')
        parent.extend(['album', ':'.join(root.split('/')[2:])])
    photoset = get_nested(tree, *parent)
    photos = [ x.lower() for x in photoset.get('photos') ]
    album = photoset.get('id')
    photo = None
    sys.stdout.write('Checking album %s (%s)\n' % (album, root.split('/')[-1]))
    for file in files:
        name = '%s/%s' % (dir, file)
        if name[-4:].lower() in VALIDEXT:
            title = '.'.join(name.split('/')[-1].split('.')[:-1]).lower()
        else:
            title = name.split('/')[-1].lower()
        if title in photos:
            sys.stderr.write('Album %s (%s) already contains photo: %s\n' % (album, root.split('/')[-1], title))
        else:
            photo = upload_photo(auth, name)
            try:
                set_photo_perms(auth, photo)
                add_album_photo(auth, album, photo)
                photos.append(title)
            except:
                delete_photo(auth, photo)
    if photo:
        set_album_photo(auth, album, photo)
    if 'dummy' in photos:
        remove_album_photo(auth, album, auth.get('dummy'))
        photos.remove('dummy')
    photoset['photos'] = photos
    return tree

def upload_dummy_photo (auth):
    return upload_photo(auth, DUMMYIMG)

def upload_photo (auth, filepath):
    url = URL.get('upload')
    attempt = 1
    complete = False
    while not complete and attempt < MAXRETRIES:
        try:
            files = {'photo': open(filepath, 'rb')}
            request = oauth_request(action=False, auth=auth, method='POST', url=url)
            response = requests.post(url, data=request, files=files)
            if response.status_code == 200:
                contents = etree.fromstring(str(response.text))
                '''
                if contents.xpath('err/@msg'):
                    error = '%s (%s)' % (contents.xpath('err/@msg')[0], contents.xpath('err/@code')[0])
                    sys.stderr.write('...failed to upload %s attempt %d: %s\n' % (filepath, attempt, error))
                    attempt = attempt + 1
                    continue
                '''
                return contents.xpath('photoid/text()')[0]
                complete = True
        except:
            sys.stderr.write('...failed to upload %s attempt %d\n' % (filepath, attempt))
        attempt = attempt + 1
    raise Exception('Failed to upload %s after %d attempts' % (filepath, MAXRETRIES))

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
    if len(sys.argv) < 2:
        usage()
    check_debug(sys.argv)

    try:
        cache = open(CACHEFILE, 'r')
        auth = cPickle.load(cache)
        cache.close()
    except:
        auth = split_url_to_dict(oauth_request())
        auth['oauth_verifier'] = oauth_authorize(auth, 'delete')

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

    if SINGLE:
        print 'SINGLE RUN'
        action = sys.argv[1]
        ACTIONS[action](auth, sys.argv[2:])
        sys.exit(0)

    attempt = 1
    complete = False
    while not complete and attempt < MAXRETRIES:
        try:
            action = sys.argv[1]
            ACTIONS[action](auth, sys.argv[2:])
            complete = True
        except:
            sys.stderr.write('...failed to complete %s attempt %d\n' % (action, attempt))
        attempt = attempt + 1
    if not complete:
        sys.stderr.write('Failed to complete %s!\n' % action)
    else:
        sys.stdout.write('Completed action: %s!\n' % action)
