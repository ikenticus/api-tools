'''
    Name:   flickr_frob_tool
    Author: ikenticus
    Date:   2014/11/14
    Notes:  Attempted to script flickr upload/download tool using frob
            which worked for download but not for the upload because
            flickr switched to oauth but did not update the API docs:
            * https://www.flickr.com/services/api/
'''

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

DUMMYIMG = 'dummy.jpg'
FROBFILE = 'flickr.frob.cache'
ROOTDIR = 'photos'  # default photo dir
PERPAGE = 100       # photos per album page
PARENT = ' : '      # parent prefix
URL = {
    'auth': 'https://api.flickr.com/services/auth/',
    'rest': 'https://api.flickr.com/services/rest/',
    'upload': 'https://up.flickr.com/services/upload/',
}

def action_download (auth, args):
    rootdir = args[0] if len(args) > 0 else ROOTDIR
    download_collections (auth, get_collections(auth), rootdir)

def action_upload (auth, args):
    rootdir = args[0] if len(args) > 0 else ROOTDIR
    online = get_collections(auth)
    # check dummy photo
    upload_directories (auth, online, rootdir)

def action_view (auth, args):
    pprint(get_collections(auth))

ACTIONS = {
    'download': action_download,
    'upload': action_upload,
    'view': action_view,
}

def check_make_dir (path):
    if not os.path.exists(path):
        os.makedirs(path)

def create_album (auth, cdict, title, photo):
    url = get_sig_url('%s?method=flickr.collections.create&title=%s&primary_photo_id=%s' \
            % (URL.get('rest'), title, photo), auth)
    try:
        response = requests.get(url)
        contents = etree.fromstring(str(response.text))
        cdict[title] = { 'id': contents.xpath('photoset/@id')[0] }
        return cdict
    except:
        raise Exception('Failed to create album: %s' % title)

def create_collection (auth, cdict, title, parent):
    url = get_sig_url('%s?method=flickr.collections.create&title=%s&parent_id=%s' \
            % (URL.get('rest'), title, parent), auth)
    try:
        response = requests.get(url)
        contents = etree.fromstring(str(response.text))
        cdict[title] = { 'id': contents.xpath('collection/@id')[0] }
        return cdict
    except:
        raise Exception('Failed to create collection: %s' % title)

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
        raise Exception('Failed to retrieve photo')

def edit_collection (auth, collection, albums, delete=0):
    url = get_sig_url('%s?method=flickr.collections.editSets&collection_id=%s&photoset_ids=%s&do_remove=%s' \
            % (URL.get('rest'), collection, albums, delete), auth)
    try:
        response = requests.get(url)
        print response.text
        contents = etree.fromstring(str(response.text))
        sys.exit(1)
    except:
        raise Exception('Failed to edit collection: %s' % collection)

def get_album_photos (auth, albumid, perpage=PERPAGE, page=1, photos=[]):
    url = get_sig_url('%s?method=flickr.photosets.getPhotos&photoset_id=%s&page=%s&per_page=%s' \
            % (URL.get('rest'), albumid, page, perpage), auth)
    try:
        response = requests.get(url)
        contents = etree.fromstring(str(response.text))
        for photo in contents.xpath('photoset/photo'):
            photos.append({
                'id': photo.xpath('@id')[0],
                'title': photo.xpath('@title')[0],
            })
        pages = int(contents.xpath('photoset/@pages')[0])
        if page < pages:
            photos = get_album_photos(auth, albumid, page=page+1, photos=photos)
        return photos
    except:
        raise Exception('Failed to retrieve album photos')

def get_albums (auth):
    albums = []
    url = get_sig_url('%s?method=flickr.photosets.getList' % URL.get('rest'), auth)
    try:
        response = requests.get(url)
        contents = etree.fromstring(str(response.text))
        for album in contents.xpath('photosets/photoset'):
            albums.append({
                'id': album.xpath('@id')[0],
                'title': album.xpath('title/text()')[0],
            })
        return albums
    except:
        raise Exception('Failed to retrieve albums')

def get_auth (frob, perms):
    url = get_sig_url('%s?frob=%s&perms=%s' % (URL.get('auth'), frob, perms))
    sys.stdout.write('\nOpen the following url in a browser and authorize it:\n%s\n\nThen click Enter/Return to continue...\n' % url)
    webbrowser.open_new(url)
    sys.stdin.readline()
    return get_token(frob)

def get_collections (auth):
    url = get_sig_url('%s?method=flickr.collections.getTree' % URL.get('rest'), auth)
    try:
        response = requests.get(url)
        contents = etree.fromstring(str(response.text))
        return loop_collection(contents.xpath('collections/collection'))
    except:
        raise Exception('Failed to retrieve collections')

def get_frob ():
    url = get_sig_url('%s?method=flickr.auth.getFrob' % URL.get('rest'))
    try:
        response = requests.get(url)
        contents = etree.fromstring(str(response.text))
        return contents.xpath('frob/text()')[0]
    except:
        raise Exception('Failed to retrieve frob')

def get_orphaned_photos (auth):
    url = get_sig_url('%s?method=flickr.photos.getNotInSet' % URL.get('rest'), auth)

def get_photo (auth, id):
    url = get_sig_url('%s?method=flickr.photos.getSizes&photo_id=%s' % (URL.get('rest'), id), auth)
    try:
        response = requests.get(url)
        contents = etree.fromstring(str(response.text))
        largest = contents.xpath('sizes/size')[-1]
        photo = {
            'label': largest.xpath('@label')[0],
            'source': largest.xpath('@source')[0],
        }
        return photo
    except:
        raise Exception('Failed to retrieve frob')

def get_sig_url (url, auth={}):
    url += '&api_key=' + APIKEY
    if auth:
        url += '&user_id=%s&auth_token=%s' % (auth.get('user'), auth.get('token'))
    params = sorted(url.split('?')[1].split('&'))
    params = ''.join([ p.replace('=', '') for p in params ])
    print params
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
        raise Exception('Failed to retrieve token')

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

def upload_directories (auth, online, rootdir):
    for root, dnames, fnames in os.walk(rootdir):
        croot = root.replace(rootdir + '/', '')
        for dname in dnames:
            if root == rootdir:
                if not online.get(dname):
                    online = create_collection (auth, online, dname, 0)
            elif dname.startswith(os.path.basename(root)):
                print 'create new year-month ' + dname
                sub = online.get(croot)
                if not sub.get('collection'):
                    sub['collection'] = {}
                if not sub.get('collection').get(dname):
                    sub['collection'] = create_collection (auth, sub['collection'], dname, sub.get('id'))
            else:
                print '\n-- Create album'
                # add dummy photo to create new album
                print '%s:%s' % (':'.join(croot.split('/'), dname))
        for fname in fnames:
            print '%s/%s' % (root, fname)
            # after uploading photos to album, remove dummy photo
            # reorder album chronologically
    pprint(online)

def upload_dummy_photo (auth):
    url = get_sig_url('%s?is_public=0&is_friend=1&is_family=1' % URL.get('upload'), auth)
    try:
        files = {'photo': open(DUMMYIMG, 'rb')}
        print url
        response = requests.post(url, files=files)
        print response.text
        #contents = etree.fromstring(str(response.text))
        #cdict[title] = { 'id': contents.xpath('photoset/@id')[0] }
        #return cdict
    except:
        raise Exception('Failed to upload dummy photo')

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

    try:
        cache = open(FROBFILE, 'r')
        auth = cPickle.load(cache)
        cache.close()
    except:
        (user, token) = get_auth(get_frob(), 'write')
        auth = { 'user': user, 'token': token, 'date': today }  
        cache = open(FROBFILE, 'w')
        cPickle.dump(auth, cache)
        cache.close()

    upload_dummy_photo(auth)

    try:
        action = sys.argv[1]
        ACTIONS[action](auth, sys.argv[2:])
    except:
        usage()
