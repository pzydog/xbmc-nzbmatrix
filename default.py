'''
 Copyright (c) 2011 pzydog

 Permission is hereby granted, free of charge, to any person
 obtaining a copy of this software and associated documentation
 files (the "Software"), to deal in the Software without
 restriction, including without limitation the rights to use,
 copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the
 Software is furnished to do so, subject to the following
 conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
 WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 OTHER DEALINGS IN THE SOFTWARE.
'''

import urllib, urllib2
import re, os, time, datetime
import xbmc, xbmcaddon, xbmcgui, xbmcplugin
import xml.parsers.expat
from xml.dom.minidom import parse, parseString

__settings__ = xbmcaddon.Addon(id='plugin.video.nzbmatrix')
__language__ = __settings__.getLocalizedString

TMDB_URL = 'http://api.themoviedb.org/2.1/Movie.imdbLookup/en/xml/'
NZBS_URL = "plugin://plugin.video.nzbs"
RSS_URL = "http://rss.nzbmatrix.com/rss.php?page=download"
BOOKMARKS_URL = "http://nzbmatrix.com/rss-bookmarks.php"

ADDON_PATH = __settings__.getAddonInfo("path")
ADDON_DATA_PATH = __settings__.getAddonInfo("profile")
CACHEDIR = os.path.join(xbmc.translatePath(ADDON_DATA_PATH), 'meta_cache')

TMDB_API_KEY = "57983e31fb435df4df77afb854740ea9"

MODE_LIST = "list"
MODE_DOWNLOAD = "download"
MODE_INCOMPLETE = "incomplete"

MODE_NZBMATRIX = "nzbmatrix"
MODE_SEARCH = "nzbmatrix&nzbmatrix=search"
MODE_BOOKMARKS = "nzbmatrix&nzbmatrix=bookmarks"

MOVIE_CATEGORIES = ['54,2,42,4', '42', '54', '2', '4']

TABLE_LISTING = [[__language__(30050), 1000], # Movies
		[__language__(30051), 42], # HD
		[__language__(30053), 54], # Brrip
		[__language__(30052), 2], # SD
		[__language__(30054), 4], # Other
		[__language__(30055), 2000], # TV
		[__language__(30051), 41], # HD
		[__language__(30052), 6], # SD
		[__language__(30054), 8], # Other
		[__language__(30056), 7], # Sport/Entertainment
		[__language__(30057), 3000], # Documentaries
		[__language__(30051), 53], # HD
		[__language__(30052), 9]] # SD

def nzbmatrix(params):
	if not(params):
		user_id = get_user_id()
		if not user_id:
			xbmc.executebuiltin("XBMC.Notification(%s, %s)" % (__language__(30030), __language__(30045)))
			exit(0)
	if not(__settings__.getSetting("nzbmatrix_username") and __settings__.getSetting("nzbmatrix_key")):
		__settings__.openSettings()
	else:
		if not os.path.exists(CACHEDIR):
			os.makedirs(CACHEDIR)
		if params:
			get = params.get
			catid = get("catid")
			nzbmatrix = get("nzbmatrix")
			url = None
			if nzbmatrix:
				if nzbmatrix == "bookmarks":
					user_id = get_user_id()
					if user_id:
						list_feed_nzbmatrix(BOOKMARKS_URL + "?userid=" + user_id + "&apikey=" + __settings__.getSetting("nzbmatrix_key"), bookmarkList=True)
					else:
						xbmcgui.Dialog().ok(__language__(30030),__language__(30040))
				elif nzbmatrix == "search":
					search_term = search('nzbmatrix')
					if search_term:
						url = generateFeedUrl(catid, search_term)
						list_feed_nzbmatrix(url)
						if not list_feed_nzbmatrix(url):
							xbmcgui.Dialog().ok(__language__(30030),__language__(30039))
				elif nzbmatrix == "add_bookmark":
					progressDialog = xbmcgui.DialogProgress()
					progressDialog.create(__language__(30030), __language__(30073))
					nzb_url = get('nzb')
					nzb_id = re.search('\?id=([0-9]+)', urllib.unquote(nzb_url), re.DOTALL)
					if(nzb_id):
						nzb_id = nzb_id.group(1)
					url = "http://api.nzbmatrix.com/v1.1/bookmarks.php?id=" + nzb_id + "&username=" + __settings__.getSetting("nzbmatrix_username") + "&apikey=" + __settings__.getSetting("nzbmatrix_key") + "&action=add"
					try:
						req = urllib2.Request(url)
						response = urllib2.urlopen(req)
						progressDialog.close()
						xbmcgui.Dialog().ok(__language__(30030),__language__(30074))
					except:
						xbmc.log("unable to load url: " + url)
						progressDialog.close()
						xbmcgui.Dialog().ok(__language__(30030),__language__(30075))
					response.close()
				elif nzbmatrix == "remove_bookmark":
					progressDialog = xbmcgui.DialogProgress()
					progressDialog.create(__language__(30030), __language__(30076))
					nzb_url = get('nzb')
					nzb_id = re.search('\?id=([0-9]+)', urllib.unquote(nzb_url), re.DOTALL)
					if(nzb_id):
						nzb_id = nzb_id.group(1)
					url = "http://api.nzbmatrix.com/v1.1/bookmarks.php?id=" + nzb_id + "&username=" + __settings__.getSetting("nzbmatrix_username") + "&apikey=" + __settings__.getSetting("nzbmatrix_key") + "&action=remove"
					try:
						req = urllib2.Request(url)
						response = urllib2.urlopen(req)
						progressDialog.close()
						xbmcgui.Dialog().ok(__language__(30030),__language__(30077))
						xbmc.executebuiltin("Container.Refresh()")
					except:
						xbmc.log("unable to load url: " + url)
						progressDialog.close()
						xbmcgui.Dialog().ok(__language__(30030),__language__(30078))
					response.close()
				elif nzbmatrix == "delete_cache":
					dirList = os.listdir(CACHEDIR)
					progressDialog = xbmcgui.DialogProgress()
					progressDialog.create(__language__(30030), __language__(30066))
					file_len = len(dirList)
					i = 0
					for fname in dirList:
						os.remove(os.path.join(CACHEDIR,fname))
						percent = int((1.0*i/file_len)*100)
						progressDialog.update(int(percent), __language__(30030), __language__(30066))
						if progressDialog.iscanceled():
							break
						i += 1
					progressDialog.close()
			elif catid:
				if catid in MOVIE_CATEGORIES:
					xbmcplugin.setContent(int(sys.argv[1]), 'movies')
				key = "&catid=" + catid
				addPosts({'title': __language__(30043), 'thumb': os.path.join(ADDON_PATH, "resources/icons/search.png")}, key, MODE_SEARCH, True)
				url = generateFeedUrl(catid)
				list_feed_nzbmatrix(url)
		else:
			# Create Main menu
			for name, catid in TABLE_LISTING:
				key = "&catid=" + str(catid)
				if catid == 1000:
					key = "&catid=54,2,42,4"
				elif catid == 2000:
					key = "&catid=41,6,8,7"
				elif catid == 3000:
					key = "&catid=53,9"
				addPosts({'title': name}, key, MODE_NZBMATRIX, True)
			addPosts({'title': __language__(30044), 'thumb': os.path.join(ADDON_PATH, "resources/icons/bookmarks.png")}, '', MODE_BOOKMARKS, True)
			addPosts({'title': __language__(30037), 'thumb': os.path.join(ADDON_PATH, "resources/icons/incomplete.png")}, '', MODE_INCOMPLETE, True)
	return
 
def addPosts(meta, url, mode, folder=False, bookmarkList=False):
	if not meta.has_key('thumb'):
		meta.update({'thumb': ''})

	listitem=xbmcgui.ListItem(meta['title'], thumbnailImage=meta['thumb'])
	if meta.has_key('fanart'):
		listitem.setProperty("Fanart_Image", meta['fanart'])
	listitem.setInfo(type="video", infoLabels=meta)
	if mode == MODE_LIST:
		cm = []
		cm_mode = MODE_DOWNLOAD
		cm_label = __language__(30070)
		if (__settings__.getSetting("auto_play").lower() == "true"):
			folder = False
		cm_url_download = NZBS_URL + '?mode=' + cm_mode + url
		cm.append((cm_label , "XBMC.RunPlugin(%s)" % (cm_url_download)))

		if(bookmarkList):
			cm.append((__language__(30072) , "XBMC.RunPlugin(%s)" % (sys.argv[0] + "?nzbmatrix=remove_bookmark&nzb=" + url)))
		else:
			cm.append((__language__(30071) , "XBMC.RunPlugin(%s)" % (sys.argv[0] + "?nzbmatrix=add_bookmark&nzb=" + url)))
			
		listitem.addContextMenuItems(cm, replaceItems=False)
		xurl = "%s?mode=%s" % (NZBS_URL,mode)
	elif mode == MODE_INCOMPLETE:
		xurl = "%s?mode=%s" % (NZBS_URL,mode)
	else:
		xurl = "%s?mode=%s" % (sys.argv[0],mode)
	xurl = xurl + url
	listitem.setPath(xurl)
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=xurl, listitem=listitem, isFolder=folder)
 
# FROM plugin.video.youtube.beta  -- converts the request url passed on by xbmc to our plugin into a dict  
def getParameters(parameterString):
	commands = {}
	splitCommands = parameterString[parameterString.find('?')+1:].split('&')
	
	for command in splitCommands: 
		if (len(command) > 0):
			splitCommand = command.split('=')
			name = splitCommand[0]
			value = splitCommand[1]
			commands[name] = value
	
	return commands

def get_node_value(parent, name, ns=""):
	if ns:
		return parent.getElementsByTagNameNS(ns, name)[0].childNodes[0].data
	else:
		if parent.getElementsByTagName(name)[0].childNodes:
			return parent.getElementsByTagName(name)[0].childNodes[0].data
		else:
			return ''

## downloads a XML file via HTTP or from cache
# @param str url The URL to the local file or to a HTTP destination
# @param bool cache Indicates whether the URL is a local on or not
# @return Document The parsed XML document
def load_xml(url, cache=False):
	try:
		if(cache):
			response = open(url, 'r')
		else:
			req = urllib2.Request(url)
			response = urllib2.urlopen(req)
	except Exception, e:
		xbmc.log("unable to load url: %s %s" % (url, e))
		response = None

	if not response:
		return False
	else:
		xml_str = response.read()
		response.close()
		try:
			parser = xml.parsers.expat.ParserCreate()
			parser.Parse(xml_str)
			return parseString(xml_str)
		except Exception, e:
			xbmc.log("Invalid response: %s %s %s" % (url, xml_str, e))
			xbmc.executebuiltin("XBMC.Notification(%s, %s)" % (__language__(30030), __language__(30046)))
			exit(0)
			return False

## Generates the URL to the RSS feeds determined by category id and search term if available
# @param str catid The ID from the category we want
# @param str search_term The search term if we're searching in a specific category
# @return str Return the URL
def generateFeedUrl(catid, search_term=""):
	english_only = "0"
	if __settings__.getSetting("english_only") == 'true':
		english_only = "1"

	term = ""
	if search_term != "":
		term = "&term=" + search_term

	url = RSS_URL + "&subcat=" + catid + "&username=" + __settings__.getSetting("nzbmatrix_username") + "&apikey=" + __settings__.getSetting("nzbmatrix_key") + "&english=" + english_only + term
	return url

## parses an rss feed and generates posts from it
# @param str feedUrl The URL to the RSS feed
# @return bool
def list_feed_nzbmatrix(feedUrl, bookmarkList=False):
	doc = load_xml(feedUrl)
	if not doc:
		return False
	re_imdb_id = 'imdb.com/title/(tt[0-9]+)'
	mode = MODE_LIST
	scrape = __settings__.getSetting("scrape_metadata")

	for item in doc.getElementsByTagName("item"):
		metadata = get_default_meta() # reset metadata
		metadata['title'] = get_node_value(item, "title")
		if metadata['title'] == "Error: No Results Found For Your Search":
			return False

		desc = get_node_value(item, "description")
		nzb = get_node_value(item, "link")
		metadata['title'] = metadata['title'].encode('utf8')
		# generate the parameters for the nzb addon
		nzb = "&nzb=" + urllib.quote_plus(nzb) + "&nzbname=" + urllib.quote_plus(metadata['title'])
		# Scrape meta information if neccessary
		if scrape == 'true':
			imdb_id = re.search(re_imdb_id, desc, re.DOTALL)
			if(imdb_id):
				imdb_id = imdb_id.group(1)
				metadata = get_metadata(imdb_id, metadata)
		addPosts(metadata, nzb, mode, bookmarkList=bookmarkList)
	return True

## Downloads the XML file found on tmdb, parses the information and returns an array with the resulting data
# @param str imdb_id e.g. tt1447479
# @param dict metadata the dictonairy to use
# @return dict
def get_metadata(imdb_id, metadata):
	
	# check if the xml info exists in the cache
	# if not create one
	xml_path = os.path.join(CACHEDIR, imdb_id + '.xml')
	xml_exists = os.path.exists(xml_path)

	# Refresh cache if older than 72 hours (make that an option?)
	cur_time = datetime.datetime.now()
	cur_time = int(time.mktime(cur_time.timetuple())) - 72 * 60 * 60
	if xml_exists:
		mod_time = os.path.getmtime(xml_path)
		if cur_time > mod_time:
			xml_exists = False # set to false so the xml is downloaded again
	if xml_exists:
		meta = load_xml(xml_path, True)
	else:
		meta = load_xml(TMDB_URL + TMDB_API_KEY + '/' + imdb_id)
		if meta:
			f = open(xml_path, 'w')
			f.write(meta.toxml().encode('utf8'))
			f.close()

	if meta:
		# extract meta information from the xml file
		for movie in meta.getElementsByTagName("movies"):
			for movie_meta in movie.getElementsByTagName("movie"):
				if __settings__.getSetting("show_scene_title") == 'false':
					metadata['title'] = get_node_value(movie_meta, "name")
				metadata['plot'] = get_node_value(movie_meta, "overview")
				metadata['rating'] = float(get_node_value(movie_meta, "rating"))
				metadata['mpaa'] = get_node_value(movie_meta, "certification")
				metadata['duration'] = get_node_value(movie_meta, "runtime")
				
				# Extract the year
				metadata['premiered'] = get_node_value(movie_meta, "released")
				if metadata['premiered'] != '':
					year = time.strptime(metadata['premiered'],"%Y-%m-%d")
					metadata['year'] = year.tm_year
				
				for images in movie_meta.getElementsByTagName("images"):
					for i in images.getElementsByTagName("image"):
						if i.getAttribute('size') == 'original' and i.getAttribute('type') == 'poster' and metadata['thumb'] == '':
							metadata['thumb'] = i.getAttribute('url')
						if i.getAttribute('size') == 'original' and i.getAttribute('type') == 'backdrop' and metadata['fanart'] == '':
							metadata['fanart'] = i.getAttribute('url')

				# Get the Genres
				for categories in movie_meta.getElementsByTagName("categories"):
					for category in categories.getElementsByTagName("category"):
						if category.getAttribute('type') == 'genre':
							metadata['genre'] += category.getAttribute('name') + ' / '
				metadata['genre'] = metadata['genre'].rstrip(' / ')
	return metadata

def get_default_meta():
	return {'title': '',
		'plot': '',
		'thumb': '',
		'fanart': '',
		'rating': 0,
		'year': 0,
		'premiered': '',
		'duration': '',
		'genre': '',
		'mpaa': '',
		'director': '',
		'actors': ''}

## For some reason the bookmarks rss feed expects a user id instead of a username...
# So we have to extract the user id from the account info
# @return str or False
def get_user_id():
	url = "http://api.nzbmatrix.com/v1.1/account.php?username=" + __settings__.getSetting("nzbmatrix_username") + "&apikey=" + __settings__.getSetting("nzbmatrix_key")
	try:
		req = urllib2.Request(url)
		response = urllib2.urlopen(req)
	except:
		xbmc.log("unable to load url: " + url)
	account_info = response.read()
	response.close()
	user_id = re.search("USERID:([0-9]+);", account_info, re.DOTALL)
	if user_id:
		return user_id.group(1)
	else:
		return False

def search(dialog_name):
	searchString = unikeyboard(__settings__.getSetting( "latestSearch" ), __language__(30038) )
	if searchString == "":
		xbmcgui.Dialog().ok(__language__(30030),__language__(30041))
	elif searchString:
		latestSearch = __settings__.setSetting( "latestSearch", searchString )
		dialogProgress = xbmcgui.DialogProgress()
		dialogProgress.create(dialog_name, __language__(30042) , searchString)
		#The XBMC onscreen keyboard outputs utf-8 and this need to be encoded to unicode
	encodedSearchString = urllib.quote_plus(searchString.decode("utf_8").encode("raw_unicode_escape"))
	return encodedSearchString

#From old undertexter.se plugin	
def unikeyboard(default, message):
	keyboard = xbmc.Keyboard(default, message)
	keyboard.doModal()
	if (keyboard.isConfirmed()):
		return keyboard.getText()
	else:
		return ""

if (__name__ == "__main__" ):
	if not (__settings__.getSetting("firstrun") and __settings__.getSetting("nzbmatrix_key")
		and __settings__.getSetting("nzbmatrix_username")):
			__settings__.openSettings()
			__settings__.setSetting("firstrun", '1')
	if (not sys.argv[2]):
		nzbmatrix(None)
	else:
		params = getParameters(sys.argv[2])
		get = params.get
		if get("mode")== MODE_LIST:
			listVideo(params)
		else:
			nzbmatrix(params)

xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True, cacheToDisc=True)