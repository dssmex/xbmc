#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from collections import OrderedDict
from copy import deepcopy
from kodi_six import xbmcplugin, xbmcgui
import json
import pickle
import re
import sys
import time

from .singleton import Singleton
from .network import getURL, getURLData, MechanizeLogin
from .logging import Log
from .itemlisting import setContentAndView
from .l10n import *
from .users import *
from .playback import PlayVideo


class PrimeVideo(Singleton):
    """ Wrangler of all things PrimeVideo.com """

    _catalog = {}  # Catalog cache
    _videodata = {'urn2gti': {}}  # Video data cache
    _catalogCache = None  # Catalog cache file name
    _videodataCache = None  # Video data cache file name
    _separator = '/'  # Virtual path separator

    def __init__(self, globalsInstance, settingsInstance):
        self._g = globalsInstance
        self._s = settingsInstance
        self._dateParserData = {
            """ Data for date string deconstruction and reassembly

                Date references:
                https://www.primevideo.com/detail/0LCQSTWDMN9V770DG2DKXY3GVF/  09 10 11 12 01 02 03 04 05
                https://www.primevideo.com/detail/0ND5POOAYD6A4THTH7C1TD3TYE/  06 07 08 09

                Languages: https://www.primevideo.com/settings/language/
            """
            'da_DK': {'deconstruct': r'^([0-9]+)\.?\s+([^\s]+)\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'januar': 1, 'februar': 2, 'marts': 3, 'april': 4, 'maj': 5, 'juni': 6, 'juli': 7, 'august': 8, 'september': 9, 'oktober': 10,
                                 'november': 11, 'december': 12}},
            'de_DE': {'deconstruct': r'^([0-9]+)\.?\s+([^\s]+)\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'januar': 1, 'februar': 2, 'märz': 3, 'april': 4, 'mai': 5, 'juni': 6, 'juli': 7, 'august': 8, 'september': 9, 'oktober': 10,
                                 'november': 11, 'dezember': 12}},
            'en_US': {'deconstruct': r'^([^\s]+)\s+([0-9]+),?\s+([0-9]+)', 'reassemble': '{2}-{0:0>2}-{1:0>2}', 'month': 0,
                      'months': {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6, 'july': 7, 'august': 8, 'september': 9, 'october': 10,
                                 'november': 11, 'december': 12}},
            'es_MX': {'deconstruct': r'^([0-9]+)\s+de\s+([^\s]+),?\s+de\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10,
                                 'noviembre': 11, 'diciembre': 12}},
            'es_ES': {'deconstruct': r'^([0-9]+)\s+de\s+([^\s]+),?\s+de\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10,
                                 'noviembre': 11, 'diciembre': 12}},
            'fi_FI': {'deconstruct': r'^([0-9]+)\.?\s+([^\s]+)\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'tammikuuta': 1, 'helmikuuta': 2, 'maaliskuuta': 3, 'huhtikuuta': 4, 'toukokuuta': 5, 'kesäkuuta': 6, 'heinäkuuta': 7, 'elokuuta': 8,
                                 'syyskuuta': 9, 'lokakuuta': 10, 'marraskuuta': 11, 'joulukuuta': 12}},
            'fr_FR': {'deconstruct': r'^([0-9]+)\s+([^\s]+)\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6, 'juillet': 7, 'aout': 8, 'août': 8, 'septembre': 9,
                                 'octobre': 10, 'novembre': 11, 'décembre': 12}},
            'hi_IN': {'deconstruct': r'^([0-9]+)\s+([^\s]+)\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'जनवरी': 1, 'फ़रवरी': 2, 'मार्च': 3, 'अप्रैल': 4, 'मई': 5, 'जून': 6, 'जुलाई': 7, 'अगस्त': 8, 'सितंबर': 9, 'अक्तूबर': 10,
                                 'नवंबर': 11, 'दिसंबर': 12}},
            'id_ID': {'deconstruct': r'^([0-9]+)\s+([^\s]+)\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6, 'juli': 7, 'agustus': 8, 'september': 9,
                                 'oktober': 10, 'november': 11, 'desember': 12}},
            'it_IT': {'deconstruct': r'^([0-9]+)\s+([^\s]+)\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4, 'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8, 'settembre': 9,
                                 'ottobre': 10, 'novembre': 11, 'dicembre': 12}},
            'nb_NO': {'deconstruct': r'^([0-9]+)\.?\s+([^\s]+)\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'januar': 1, 'februar': 2, 'mars': 3, 'april': 4, 'mai': 5, 'juni': 6, 'juli': 7, 'august': 8, 'september': 9, 'oktober': 10,
                                 'november': 11, 'desember': 12}},
            'nl_NL': {'deconstruct': r'^([0-9]+)\s+([^\s]+)\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6, 'juli': 7, 'augustus': 8, 'september': 9,
                                 'oktober': 10, 'november': 11, 'december': 12}},
            'pl_PL': {'deconstruct': r'^([0-9]+)\s+([^\s]+)\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'stycznia': 1, 'lutego': 2, 'marca': 3, 'kwietnia': 4, 'maja': 5, 'czerwca': 6, 'lipca': 7, 'sierpnia': 8, 'września': 9,
                                 'października': 10, 'listopada': 11, 'grudnia': 12}},
            'pt_BR': {'deconstruct': r'^([0-9]+)\s+de\s+([^\s]+),?\s+de\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10,
                                 'novembro': 11, 'dezembro': 12}},
            'ru_RU': {'deconstruct': r'^([0-9]+)\s+([^\s]+)\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8, 'сентября': 9,
                                 'октября': 10, 'ноября': 11, 'декабря': 12}},
            'sv_SE': {'deconstruct': r'^([0-9]+)\s+([^\s]+)\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'januari': 1, 'februari': 2, 'mars': 3, 'april': 4, 'maj': 5, 'juni': 6, 'juli': 7, 'augusti': 8, 'september': 9, 'oktober': 10,
                                 'november': 11, 'december': 12}},
            'ta_IN': {'deconstruct': r'^([0-9]+)\s+([^\s]+),?\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'ஜனவரி': 1, 'பிப்ரவரி': 2, 'மார்ச்': 3, 'ஏப்ரல்': 4, 'மே': 5, 'ஜூன்': 6, 'ஜூலை': 7, 'ஆகஸ்ட்': 8, 'செப்டம்பர்': 9,
                                 'அக்டோபர்': 10, 'நவம்பர்': 11, 'டிசம்பர்': 12}},
            'te_IN': {'deconstruct': r'^([0-9]+)\s+([^\s]+),?\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'జనవరి': 1, 'ఫిబ్రవరి': 2, 'మార్చి': 3, 'ఏప్రిల్': 4, 'మే': 5, 'జూన్': 6, 'జులై': 7, 'ఆగస్టు': 8, 'సెప్టెంబర్': 9, 'అక్టోబర్': 10,
                                 'నవంబర్': 11, 'డిసెంబర్': 12}},
            'tr_TR': {'deconstruct': r'^([0-9]+)\s+([^\s]+)\s+([0-9]+)', 'reassemble': '{2}-{1:0>2}-{0:0>2}', 'month': 1,
                      'months': {'ocak': 1, 'şubat': 2, 'mart': 3, 'nisan': 4, 'mayıs': 5, 'haziran': 6, 'temmuz': 7, 'ağustos': 8, 'eylül': 9,
                                 'ekim': 10, 'kasım': 11, 'aralık': 12}},
            'zh_CN': {'deconstruct': r'^([0-9]+)年([0-9]+)月([0-9]+)日', 'reassemble': '{0}-{1:0>2}-{2:0>2}', 'month': 1},
            'zh_TW': {'deconstruct': r'^([0-9]+)年([0-9]+)月([0-9]+)日', 'reassemble': '{0}-{1:0>2}-{2:0>2}', 'month': 1},
        }
        self._LoadCache()

    def _Flush(self, bFlushCacheData=True, bFlushVideoData=False):
        """ Cache catalog and video data """

        if bFlushCacheData:
            with open(self._catalogCache, 'wb+') as fp:
                pickle.dump(self._catalog, fp)
        if bFlushVideoData:
            with open(self._videodataCache, 'w+') as fp:
                bPretty = self._s.verbLog
                json.dump(self._videodata, fp, indent=2 if bPretty else None, separators=None if bPretty else (',', ':'), sort_keys=True)

    def _LoadCache(self):
        """ Load cached catalog and video data """

        from os.path import join as OSPJoin
        from xbmcvfs import exists, delete

        self._catalogCache = OSPJoin(self._g.DATA_PATH, 'PVCatalog{}.pvcp'.format(self._g.MarketID))
        self._videodataCache = OSPJoin(self._g.DATA_PATH, 'PVVideoData{}.pvdp'.format(self._g.MarketID))

        if exists(self._videodataCache):
            try:
                with open(self._videodataCache, 'r') as fp:
                    data = json.load(fp)
                if 'urn2gti' not in data:
                    raise Exception('Old, unsafe cache data')
                self._videodata = data
            except:
                Log('Removing corrupted cache file “{}”'.format(self._videodataCache), Log.DEBUG)
                delete(self._videodataCache)
                self._g.dialog.notification('Corrupted video cache', 'Unable to load the video cache data', xbmcgui.NOTIFICATION_ERROR)

        if exists(self._catalogCache):
            try:
                with open(self._catalogCache, 'rb') as fp:
                    cached = pickle.load(fp)
                if time.time() < cached['expiration']:
                    self._catalog = cached
            except:
                Log('Removing corrupted cache file “{}”'.format(self._catalogCache), Log.DEBUG)
                delete(self._catalogCache)
                self._g.dialog.notification('Corrupted catalog cache', 'Unable to load the catalog cache data', xbmcgui.NOTIFICATION_ERROR)

    def _BeautifyText(self, title):
        """ Correct stylistic errors in Amazon's titles """

        for t in [(r'\s+-\s*([^&])', r' – \1'),  # Convert dash from small to medium where needed
                  (r'\s*-\s+([^&])', r' – \1'),  # Convert dash from small to medium where needed
                  (r'^\s+', ''),  # Remove leading spaces
                  (r'\s+$', ''),  # Remove trailing spaces
                  (r' {2,}', ' '),  # Remove double spacing
                  (r'\.\.\.', '…')]:  # Replace triple dots with ellipsis
            title = re.sub(t[0], t[1], title)
        return title

    def _FQify(self, URL):
        """ Makes sure to provide correct fully qualified URLs """
        base = self._g.BaseUrl
        if '://' in URL:  # FQ
            return URL
        elif URL.startswith('//'):  # Specified domain, same schema
            return base.split(':')[0] + ':' + URL
        elif URL.startswith('/'):  # Relative URL
            return base + URL
        else:  # Hope and pray we never reach this ¯\_(ツ)_/¯
            return base + '/' + URL

    def _GrabJSON(self, url, bRaw=False):
        """ Extract JSON objects from HTMLs while keeping the API ones intact """

        def Unescape(text):
            """ Unescape various html/xml entities in dictionary values, courtesy of Fredrik Lundh """

            def fixup(m):
                """ Unescape entities except for double quotes, lest the JSON breaks """
                try:
                    from html.entities import name2codepoint
                except:
                    from htmlentitydefs import name2codepoint

                text = m.group(0)  # First group is the text to replace

                # Unescape if possible
                if text[:2] == "&#":
                    # character reference
                    try:
                        bHex = ("&#x" == text[:3])
                        char = int(text[3 if bHex else 2:-1], 16 if bHex else 10)
                        if 34 == char:
                            text = u'\\"'
                        else:
                            try:
                                text = unichr(char)
                            except NameError:
                                text = chr(char)
                    except ValueError:
                        pass
                else:
                    # named entity
                    char = text[1:-1]
                    if 'quot' == char:
                        text = u'\\"'
                    elif char in name2codepoint:
                        char = name2codepoint[char]
                        try:
                            text = unichr(char)
                        except NameError:
                            text = chr(char)
                return text

            text = re.sub('&#?\\w+;', fixup, text)
            try:
                text = text.encode('latin-1').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass

            return text

        def Merge(o, n):
            """ Merge JSON objects with multiple multi-level collisions """
            if (not n) or (o == n):  # Nothing to do
                return
            elif (type(n) == list) or (type(n) == set):  # Insert into list/set
                for item in n:
                    if item not in o:
                        if type(n) == list:
                            o.append(item)
                        else:
                            o.add(item)
            elif type(n) == dict:
                for k in list(n):  # list() instead of .keys() to avoid py3 iteration errors
                    if k not in o:
                        o[k] = n[k]  # Insert into dictionary
                    else:
                        Merge(o[k], n[k])  # Recurse
            else:
                Log('Collision detected during JSON objects merging, overwriting and praying', Log.WARNING)
                o = n

        def Prune(d):
            """ Prune some commonly found sensitive info from JSON response bodies """
            if not d:
                return

            l = d
            if isinstance(l, dict):
                for k in list(l):  # list() instead of .keys() to avoid py3 iteration errors
                    if k == 'strings':
                        l[k] = {s: l[k][s] for s in ['AVOD_DP_season_selector'] if s in l[k]}
                    if (not l[k]) or (k in ['context', 'params', 'playerConfig', 'refine']):
                        del l[k]
                l = d.values()
            for v in l:
                if isinstance(v, dict) or isinstance(v, list):
                    Prune(v)

        try:
            from urlparse import urlparse, parse_qs
            from urllib import urlencode
        except:
            from urllib.parse import urlparse, parse_qs, urlencode
        if url.startswith('/search/'):
            np = urlparse(url)
            qs = parse_qs(np.query)
            if 'from' in list(qs):  # list() instead of .keys() to avoid py3 iteration errors
                qs['startIndex'] = qs['from']
                del qs['from']
            np = np._replace(path='/gp/video/api' + np.path, query=urlencode([(k, v) for k, l in qs.items() for v in l]))
            url = np.geturl()

        r = getURL(self._FQify(url), silent=True, useCookie=True, rjson=False)
        if not r:
            return None
        try:
            r = r.strip()
            if '{' == r[0:1]:
                o = json.loads(Unescape(r))
                if not bRaw:
                    Prune(o)
                return o
        except:
            pass

        matches = re.findall(r'\s*(?:<script type="text/template">|state:)\s*({[^\n]+})\s*(?:,|</script>)\s*', r)
        if not matches:
            Log('No JSON objects found in the page', Log.ERROR)
            return None

        # Create a single object containing all the data from the multiple JSON objects in the page
        o = {}
        for m in matches:
            m = json.loads(Unescape(m))
            if 'props' not in m:
                if 'widgets' in m:
                    m = m['widgets']['Storefront']
            else:
                m = m['props']

                if not bRaw:
                    # Prune useless/sensitive info
                    for k in list(m):  # list() instead of .keys() to avoid py3 iteration errors
                        if (not m[k]) or (k in ['copyright', 'links', 'logo', 'params', 'playerConfig', 'refine']):
                            del m[k]
                    if 'state' in m:
                        st = m['state']
                        for k in list(st):  # list() instead of .keys() to avoid py3 iteration errors
                            if not st[k]:
                                del st[k]
                            elif k in ['features', 'customerPreferences']:
                                del st[k]

            # Prune sensitive context info and merge into o
            if not bRaw:
                Prune(m)
            Merge(o, m)

        return o if o else None

    def _TraverseCatalog(self, path, bRefresh=False):
        """ Extract current node, grandparent node and their names """

        try:
            from urllib.parse import unquote_plus
        except:
            from urllib import unquote_plus

        # Fix the unquote_plus problem with unicode_literals by encoding to latin-1 (byte string) and then decoding
        pathList = [unquote_plus(p) for p in path.split(self._separator)]
        for k in range(len(pathList)):
            try:
                pathList[k] = pathList[k].encode('latin-1').decode('utf-8')
            except: pass

        if 0 == len(self._catalog):
            self.BuildRoot()

        # Traverse
        node = self._catalog
        pathLen = len(pathList)
        for i in range(0, pathLen):
            nodeName = pathList[i]

            # Stop one short while refreshing, due to python mutability reasons
            if bRefresh and (i == (pathLen - 1)):
                break
                
            # Populate children list to avoid favourite/library traversal errors            
            if 'children' in node:
                for cid in node['children']:
                    if cid not in node:
                        node[cid] = {}
                        try:
                            if 0 == len(self._videodata[cid]['children']):
                                node[cid]['lazyLoadURL'] = self._videodata[cid]['ref']
                        except: pass
            
            if nodeName not in node:
                self._g.dialog.notification('Catalog error', 'Catalog path not available…', xbmcgui.NOTIFICATION_ERROR)
                return (None, None)
            elif 'lazyLoadURL' in node[nodeName]:
                self._LazyLoad(node[nodeName], pathList[0:1 + i])
            node = node[nodeName]

        return (node, pathList)

    def BrowseRoot(self):
        """ Build and load the root PrimeVideo menu """

        if 0 == len(self._catalog):
            ''' Build the root catalog '''
            if not self.BuildRoot():
                return
        self.Browse('root')

    def BuildRoot(self):
        """ Parse the top menu on primevideo.com and build the root catalog """

        home = self._GrabJSON(self._g.BaseUrl)
        if not home:
            return False

        self._catalog['root'] = OrderedDict()

        #Log('home cnt: {}'.format(home))

        # Insert the watchlist
        try:
            watchlist = next((x for x in home['yourAccount']['links'] if '/watchlist/' in x['href']), None)
            self._catalog['root']['Watchlist'] = {'title': self._BeautifyText(watchlist['text']), 'lazyLoadURL': watchlist['href']}
        except:
            Log('Watchlist link not found', Log.ERROR)

        # Insert the main sections, in order
        try:
            for link in home['mainMenu']['links']:
                self._catalog['root'][link['text']] = {'title': self._BeautifyText(link['text']), 'lazyLoadURL': link['href']}
                if '/home/' in link['href']:
                    self._catalog['root'][link['text']]['lazyLoadData'] = home
        except:
            self._g.dialog.notification('PrimeVideo error', 'Unable to find the navigation menu for primevideo.com', xbmcgui.NOTIFICATION_ERROR)
            Log('Unable to parse the navigation menu for primevideo.com', Log.ERROR)
            return False

        # Insert the searching mechanism
        try:
            sfa = home['searchBar']['searchFormAction']
            # Build the query parametrization
            query = ''
            if 'query' in sfa:
                query += '&'.join(['{}={}'.format(k, v) for k, v in sfa['query'].items()])
            query = query if not query else query + '&'
            self._catalog['root']['Search'] = {
                'title': self._BeautifyText(home['searchBar']['searchFormPlaceholder']),
                'verb': 'pv/search/',
                'endpoint': '{}?{}phrase={{}}'.format(sfa['partialURL'], query)
            }
        except:
            Log('Search functionality not found', Log.ERROR)

        # Set the expiration in 11 hours and flush to disk
        self._catalog['expiration'] = 39600 + int(time.time())

        self._Flush()

        return True

    def Browse(self, path, forceSort=None):
        """ Display and navigate the menu for PrimeVideo users """

        # Add multiuser menu if needed
        if (self._s.multiuser) and ('root' == path) and (1 < len(loadUsers())):
            li = xbmcgui.ListItem(getString(30134).format(loadUser('name')))
            li.addContextMenuItems(self._g.CONTEXTMENU_MULTIUSER)
            xbmcplugin.addDirectoryItem(self._g.pluginhandle, '{}pv/browse/root{}SwitchUser'.format(self._g.pluginid, self._separator), li, isFolder=False)
        if ('root' + self._separator + 'SwitchUser') == path:
            if switchUser():
                self.BuildRoot()
            return

        try:
            from urllib.parse import quote_plus
        except ImportError:
            from urllib import quote_plus
        
        node, breadcrumb = self._TraverseCatalog(path)
        if None is node:
            return
            
        # Populate children list with empty references
        nodeName = breadcrumb[-1]
        if (nodeName in self._videodata) and ('children' in self._videodata[nodeName]):
            for c in self._videodata[nodeName]['children']:
                if c not in node:
                    node[c] = {}                                        

        #Debug
        Log('nodeName: {}'.format(nodeName), Log.DEBUG)

        folderType = 0 if 'root' == path else 1
        
        #for key in [k for k in node if k not in ['ref', 'verb', 'title', 'metadata', 'parent', 'siblings', 'children']]:
        for key in node:
          if key not in ['ref', 'verb', 'title', 'metadata', 'parent', 'siblings', 'children']:  
        
            url = self._g.pluginid
                        
            if key in self._videodata:
                entry = deepcopy(self._videodata[key])              
            else:
                entry = node[key]                
                        
            title = entry['title'] if 'title' in entry else nodeName
            
            #Debug
            Log('item: {}'.format(title), Log.DEBUG)
            Log('key: {}'.format(key), Log.DEBUG)            
            
            itemPathURI = '{}{}{}'.format(path, self._separator, quote_plus(key.encode('utf-8')))

            # Squash single season tv shows
            try:
                if 'tvshow' == self._videodata[key]['metadata']['videometa']['mediatype']:
                    if 1 == len(self._videodata[key]['children']):
                        childgti = self._videodata[key]['children'][0]
                        entry = deepcopy(self._videodata[childgti])
                        itemPathURI += '{}{}'.format(self._separator, quote_plus(childgti.encode('utf-8')))
            except: pass

            # Find out if item's a video leaf
            bIsVideo = False
            try: 
                bIsVideo = self._videodata[key]['metadata']['videometa']['mediatype'] in ['episode', 'movie', u'episode', u'movie']
                #Log('self._videodata[key]: {}'.format(self._videodata[key]))
            except: pass
            
            #Log('Found Item:{0} (key:{1}) (Video={2})'.format(title, key, bIsVideo))
            

            # Can we refresh the cache on this/these item(s)?
            bCanRefresh = ('ref' in entry) or ('lazyLoadURL' in entry)
            if ('children' in entry) and (0 < len(entry['children'])):
                bCanRefresh |= (0 < len([k for k in entry['children'] if (k in self._videodata) and ('ref' in self._videodata[k])]))

            if bIsVideo:
                iTrailer=0
                if 'streamingType' in self._videodata[key]['metadata']:
                    #['Feature' : 0, 'Trailer' : 1, 'LiveStreaming' : 2]
                    if self._videodata[key]['metadata']['streamingType'] == 'LiveStreaming':
                        iTrailer = 2
                url += '?mode=PlayVideo&name={}&asin={}&trailer={}'.format(self._videodata[key]['metadata']['compactGTI'], key, iTrailer)
            elif 'verb' in entry:
                url += entry['verb']
                itemPathURI = ''
            else:
                url += 'pv/browse/' + itemPathURI
            # Log('Encoded PrimeVideo URL: {}'.format(url), Log.DEBUG)
            item = xbmcgui.ListItem(title)
           
            # Actions
            actions = []
            if bCanRefresh and (0 < len(itemPathURI)):
                # Log('Encoded PrimeVideo refresh URL: pv/refresh/{}'.format(itemPathURI), Log.DEBUG)
                actions.append(('Refresh', 'RunPlugin({}pv/refresh/{})'.format(self._g.pluginid, itemPathURI)))

            if 'actions' in entry:
                for a in entry['actions']:
                    #Log('Encoded PrimeVideo actions "{}" URL: pv/action{}'.format(a['title'], a['url']))
                    actions.append((a['title'], 'RunPlugin({}pv/action{})'.format(self._g.pluginid, a['url'])))

            if 0 < len(actions):
                item.addContextMenuItems(actions)

            # In case of tv shows find the oldest season and apply its art
            try:
                if ('tvshow' == entry['metadata']['videometa']['mediatype']) and (1 < len(entry['children'])):
                    sn = None
                    snid = None
                    for child in entry['children']:
                        try:
                            childsn = self._videodata[child]['metadata']['videometa']['season']
                            if (None is sn) or (sn > childsn):
                                sn = childsn
                                snid = child
                        except: pass
                    if snid:
                        entry['metadata']['artmeta'] = self._videodata[snid]['metadata']['artmeta']
                        entry['metadata']['videometa']['plot'] = getString(30253).format(len(entry['children']))  # "# series" as plot/description
            except: pass

            folder = True
            if 'metadata' in entry:
                m = entry['metadata']
                if 'artmeta' in m:
                    item.setArt(m['artmeta'])
                if 'videometa' in m:
                    # https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
                    item.setInfo('video', m['videometa'])
                    try:
                        folderType = {'movie': 5, 'live': 5, 'episode': 4, 'tvshow': 2, 'season': 3}[m['videometa']['mediatype']]
                    except:
                        folderType = 2  # Default to category

                    if bIsVideo:
                        folder = False
                        item.setProperty('IsPlayable', 'true')
                        item.setInfo('video', {'title': title})
                        if 'runtime' in m:
                            item.setInfo('video', {'duration': m['runtime']})
                            item.addStreamInfo('video', {'duration': m['runtime']})

            # If it's a video leaf without an actual video, something went wrong with Amazon servers, just hide it
            if (not folder) or (4 > folderType):
                xbmcplugin.addDirectoryItem(self._g.pluginhandle, url, item, isFolder=folder)
            del item

        # Set sort method and view
        # https://codedocs.xyz/xbmc/xbmc/group__python__xbmcplugin.html#ga85b3bff796fd644fb28f87b136025f40
        '''
        xbmcplugin.addSortMethod(self._g.pluginhandle, [
            xbmcplugin.SORT_METHOD_NONE,  # Root
            xbmcplugin.SORT_METHOD_NONE,  # Category list
            xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE,  # Category
            xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE,  # TV Show (Seasons list)
            xbmcplugin.SORT_METHOD_EPISODE,  # Season (Episodes list)
            xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE,  # Movies list
        ][folderType] if None is forceSort else forceSort)
        '''
        xbmcplugin.addSortMethod(self._g.pluginhandle, [
            xbmcplugin.SORT_METHOD_NONE,               # Root
            xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE,   # Category list
            xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE,   # Category
            xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE,   # TV Show (Seasons list)
            xbmcplugin.SORT_METHOD_EPISODE,            # Season (Episodes list)
            xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE,   # Movies list (keep web order)
        ][folderType] if None is forceSort else forceSort)

        if 'false' == self._g.addon.getSetting("viewenable"):
            # Only vfs and videos to keep Kodi's watched functionalities
            folderType = 0 if 2 > folderType else 1
        else:
            # Actual views, set the main categories as vfs
            folderType = 0 if 2 > folderType else 2

        setContentAndView([None, 'videos', 'series', 'season', 'episode', 'movie'][folderType])
        
        #more Sort Methods for movies
        if folderType == 5:
            add
        

    def Search(self):
        """ Provide search functionality for PrimeVideo """

        searchString = self._g.dialog.input(getString(24121)).strip(' \t\n\r')
        if 0 == len(searchString):
            xbmcplugin.endOfDirectory(self._g.pluginhandle, succeeded=False)
            return
        Log('Searching "{}"…'.format(searchString), Log.INFO)
        self._catalog['search'] = OrderedDict([('lazyLoadURL', self._catalog['root']['Search']['endpoint'].format(searchString))])
        self.Browse('search', xbmcplugin.SORT_METHOD_NONE)

    def Refresh(self, path):
        """ Provides cache refresh functionality """

        refreshes = []
        node, breadcrumb = self._TraverseCatalog(path, True)
        if None is node:
            return

        # Only refresh if previously loaded. If not loaded, and specifically asked, perform a full (lazy) loading
        k = breadcrumb[-1]
        if (k not in node) and (k in self._videodata):
            node[k] = {}

        if 'lazyLoadURL' in node[k]:
            refreshes.append((node[k], breadcrumb, False))
        else:
            bShow = False
            if 'ref' in node[k]:  # ref's in the cache already
                Log('Refreshing element in the cache: {}'.format(k), Log.DEBUG)
                targetURL = node[k]['ref']
            elif 'ref' in self._videodata[k]:  # Season
                Log('Refreshing season: {}'.format(k), Log.DEBUG)
                targetURL = self._videodata[k]['ref']
            else:  # TV Show
                Log('Refreshing Show: {}'.format(k), Log.DEBUG)
                bShow = True
                for season in [k for k in self._videodata[k]['children'] if (k in self._videodata) and ('ref' in self._videodata[k])]:
                    if (season in node[k]) and ('lazyLoadURL' in node[k][season]):
                        bRefresh = False
                    else:
                        bRefresh = True
                        node[k][season] = {'lazyLoadURL': self._videodata[season]['ref']}
                    refreshes.append((node[k][season], breadcrumb + [season], bRefresh))

            if not bShow:
                # Reset the basic metadata
                title = node[k]['title'] if 'title' in node[k] else None
                node[k] = {'lazyLoadURL': targetURL}
                if title:
                    node[k]['title'] = title
                refreshes.append((node[k], breadcrumb, True))

        from contextlib import contextmanager

        @contextmanager
        def _busy_dialog():
            xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
            try:
                yield
            finally:
                xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

        with _busy_dialog():
            for r in refreshes:
                Log('Refresh params: {}'.format(r))
                self._LazyLoad(r[0], r[1], r[2])
                
    def Action(self, sPath, param):
        """ Provides actions functionality """        
        sURL = '{0}/{1}{2}'.format(g.BaseUrl, sPath, param)
        #login
        amzLang = None
        if None is not sURL:
            # Find the locale amazon's using
            cj = MechanizeLogin()
            if cj:
                amzLang = cj.get('lc-main-av', path='/')
        amzLang = amzLang if amzLang else 'es_MX'        
        
        #get action
        r = getURL(self._FQify(sURL), silent=True, useCookie=True, rjson=False, postdata=None)
                

    def _LazyLoad(self, obj, breadcrumb=None, bCacheRefresh=False):
        """ Loader and parser of all the PrimeVideo.com queries """

        def MaxSize(imgUrl):
            """ Strip the dynamic resize triggers from the URL (and other effects, such as blur) """

            return re.sub(r'\._.*_\.', '.', imgUrl)

        def ExtractURN(url):
            """ Extract the unique resource name identifier """

            ret = re.search(r'(?:/gp/video)?/d(?:p|etail)/([^/]+)/', url)
            return None if not ret else ret.group(1)

        def DelocalizeDate(lang, datestr):
            """ Convert language based timestamps into YYYY-MM-DD """

            if lang not in self._dateParserData:
                Log('Unable to decode date "{}": language "{}" not supported'.format(datestr, lang), Log.WARNING)
                return datestr
            l = lang
            try:
                p = re.search(self._dateParserData[l]['deconstruct'], datestr.lower())
            except: pass
            if None is p:
                #Log('Unable to parse date "{}" with language "{}"{}'.format(datestr, l, '' if 'en_US' == l else ': trying english'), Log.WARNING)
                if 'en_US' == l:
                    return datestr
                # Sometimes Amazon returns english everything, let's try to figure out if this is the case
                l = 'en_US'
                try:
                    p = re.search(self._dateParserData[l]['deconstruct'], datestr.lower())
                except: pass
                if None is p:
                    Log('Unable to parse date "{}" with language "{}": new locale or format changed?'.format(datestr, l), Log.WARNING)
                    return datestr
            p = list(p.groups())
            m = self._dateParserData[l]['month']
            if p[m].isdigit():
                p[m] = int(p[m])
            else:
                try:
                    p[m] = self._dateParserData[l]['months'][p[m]]
                except:
                    #Log('Unable to parse month of "{}" with language "{}", trying with "{}" localized months'.format(datestr, l, lang), Log.WARNING)
                    try:
                        p[m] = {x[0:3]: self._dateParserData[lang]['months'][x] for x in self._dateParserData[lang]['months']}[p[m]]
                    except:
                        Log('Unable to parse date "{}" with any known language combination'.format(datestr), Log.WARNING)
                        return datestr
            return self._dateParserData[l]['reassemble'].format(p[0], p[1], p[2])

        def NotifyUser(msg, bForceDisplay=False):
            """ Pop up messages while scraping to inform users of progress """

            if not hasattr(NotifyUser, 'lastNotification'):
                NotifyUser.lastNotification = 0
            if bForceDisplay or (NotifyUser.lastNotification < time.time()):
                # Only update once every other second, to avoid endless message queue
                NotifyUser.lastNotification = 1 + time.time()
                self._g.dialog.notification(self._g.addon.getAddonInfo('name'), msg, time=1000, sound=False)

        def MultiRegexParsing(content, o):
            """ Takes a dictionary of regex and applies them to content, returning a filtered dictionary of results """

            for i in o:
                o[i] = re.search(o[i], content, flags=re.DOTALL)
                if None is not o[i]:
                    o[i] = o[i].groups()
                    o[i] = Unescape(o[i][0]) if 1 == len(o[i]) else list(o[i])
                    if 'image' == i:
                        o[i] = MaxSize(o[i])
                    elif 'season' == i:
                        o[i] = {'locale': Unescape(o[i][0]), 'season': int(o[i][1]), 'format': Unescape('{} {}'.format(o[i][0], o[i][1]))}
                    elif ('episode' == i) or ('year' == i):
                        o[i] = int(o[i])
                    elif ('cast' == i) or ('genre' == i) or ('director' == i):
                        o[i] = re.sub(r'\s*</?(a|span|input|label.*?/label)\s*[^>]*>\s*', '', o[i][1])  # Strip everything useless
                        o[i] = re.split(r'\s*[,;]\s*', o[i])
                        # Cast is always to be sent as a list, single string is only required/preferred for Genre and Director
                        if ('cast' != i) and (1 == len(o[i])):
                            o[i] = o[i][0]
                    elif 'rating' == i:
                        o[i] = int(o[i][0]) + (int(o[i][1]) / 10.0)
                    elif 'premiered' == i:
                        o[i] = DelocalizeDate(amzLang, o[i])
            return o

        def AddSeason(oid, o, title, thumbnail, url):
            """ Given a season, adds TV Shows to the catalog """
            urn = ExtractURN(url)
            parent = None
            season = {}
            bUpdatedVideoData = False
            if urn not in self._videodata['urn2gti']:
                # Find the show the season belongs to
                bUpdatedVideoData |= ParseSinglePage(oid, season, False, url=url)
                if urn in self._videodata['urn2gti']:
                    seasonGTI = self._videodata['urn2gti'][urn]
                try:
                    # Query an episode to find its ancestors
                    family = getURLData('catalog/GetPlaybackResources', self._videodata[seasonGTI]['children'][0], silent=True, extra=True, useCookie=True,
                                        opt='&titleDecorationScheme=primary-content', dRes='CatalogMetadata')[1]['catalogMetadata']['family']['tvAncestors']
                    # Grab the 'SHOW' ancestor ({SHOW: [{SEASON: [EPISODE, …], …}])
                    parent = [a['catalog'] for a in family if 'SHOW' == a['catalog']['type']][0]
                except: pass
                if parent:
                    # {'id': gti, 'title': …, 'type': 'SHOW', …}
                    pid = parent['id']
                    self._videodata[seasonGTI]['parent'] = pid
                    self._videodata[pid] = {'title': parent['title'], 'metadata': {'videometa': {'mediatype': 'tvshow'}}, 'children': [seasonGTI]}
                    for gti in self._videodata[seasonGTI]['siblings']:
                        self._videodata[gti]['parent'] = pid
                        if gti not in self._videodata[pid]['children']:
                            self._videodata[pid]['children'].append(gti)
                    parent = pid
                    bUpdatedVideoData = True
            else:
                if urn in self._videodata['urn2gti'] and 'parent' in self._videodata[self._videodata['urn2gti'][urn]]:
                    parent = self._videodata[self._videodata['urn2gti'][urn]]['parent']

            bSeasonOnly = (not parent) or (oid == parent)
            if not bSeasonOnly:
                o[parent] = deepcopy(self._videodata[parent])
                o = o[parent]
            for sid in season:
                o[sid] = season[sid]
            return bUpdatedVideoData

        def AddChannel(oid, o, title, thumbnail, url):
            """ Add channel descriptions """
            bUpdatedVideoData = True
            o[title] = {
                'title': self._BeautifyText(title),
                'lazyLoadURL': url,
                'metadata': {
                    'artmeta': {
                        'thumb': thumbnail
                    },
                    'videometa': {
                        'mediatype': 'season',
                    }
                }
            }
            return bUpdatedVideoData

        def AddLiveChannel(oid, item):
            #get data
            sChannelId = item['playbackAction']['channelId']
            sTitle = self._BeautifyText(item['title'])
            sCompactGTI = item['playbackAction']['sessionID']
            sImage = item['image']['url']
            sYear = item['releaseYear']
            
            #add object
            o[sChannelId] = {
                'title': sTitle,
                'metadata': {
                    'compactGTI' : sCompactGTI,
                    'streamingType' : 'LiveStreaming',
                    'artmeta': {
                        'thumb': sImage,
                        'poster': sImage
                    },
                    'videometa': {
                        'mediatype': 'movie',
                        'mpaa': 'NR',
                        'plot': '{0} ({1})'.format(sTitle, sYear),
                        'year': sYear
                    }
                }             
            }   
            
            bUpdated = True
            self._videodata[sChannelId] = o[sChannelId]
                                 
            return bUpdated            
            
        def ParseSinglePage(oid, o, bCacheRefresh, data=None, url=None):
            """ Parse PrimeVideo.com single movie/season pages.
                `url` is discarded in favour of `data`, if present.
            """
            urn = ExtractURN(url)

            # Load from cache, if available
            if (not bCacheRefresh) and (urn in self._videodata['urn2gti']) and (self._videodata['urn2gti'][urn] in self._videodata):
                gti = self._videodata['urn2gti'][urn]
                vd = self._videodata[gti]
                # Movie
                if 'children' not in vd:
                    if gti not in o:
                        o[gti] = vd
                    return False

                # TV Series
                bEpisodesOnly = oid == gti
                siblings = [] if bEpisodesOnly else vd['siblings'][:]
                siblings.append(gti)
                siblings = sorted(siblings, key=(lambda k: self._videodata[k]['metadata']['videometa']['season']))
                for gti in siblings:
                    # Add season if we're not inside a season already
                    if (not bEpisodesOnly) and (gti not in o):
                        o[gti] = deepcopy(self._videodata[gti])
                        dest = o[gti]
                    else:
                        o = deepcopy(self._videodata[gti])
                        dest = o
                    # Add cached episodes
                    for c in dest['children']:
                        if c not in dest:
                            dest[c] = {}
                return False

            if url:
                url = self._FQify(url)
            if not data:
                if not url:
                    return False
                data = self._GrabJSON(url)
                if not data:
                    NotifyUser(getString(30256), True)
                    Log('Unable to fetch the url: {}'.format(url), Log.ERROR)
                    return False
                # from .logging import LogJSON
                # LogJSON(data, url)

            # Video/season/movie data are in the `state` field of the response
            if 'state' not in data:
                return False

            state = data['state']  # Video info
            GTIs = []  # List of inserted GTIs
            parents = {}  # Map of parents
            bUpdated = False  # Video data updated

            # Seasons (episodes are now listed in self too)
            # Only add seasons if we are not inside a season already
            if ('self' in state) and (oid not in state['self']):
                # "self": {"amzn1.dv.gti.[…]": {"gti": "amzn1.dv.gti.[…]", "link": "/detail/[…]"}}
                for gti in [k for k in state['self'] if 'season' == state['self'][k]['titleType']]:
                    s = state['self'][gti]
                    gti = s['gti']
                    if gti not in self._videodata:
                        o[gti] = {('ref' if state['pageTitleId'] == gti else 'lazyLoadURL'): s['link']}
                        self._videodata[gti] = {'ref': s['link'], 'children': [], 'siblings': []}
                        bUpdated = True
                    else:
                        o[gti] = self._videodata[gti]
                    GTIs.append(gti)
                    siblings = [k for k, ss in state['self'].items() if k != gti and ss['titleType'] == s['titleType']]

                    if not 'siblings' in self._videodata[gti]:
                        self._videodata[gti]['siblings'] = {}

                    if siblings != self._videodata[gti]['siblings']:
                        self._videodata[gti]['siblings'] = siblings
                        bUpdated = True

            # Episodes lists
            if 'collections' in state:
                # "collections": {"amzn1.dv.gti.[…]": [{"titleIds": ["amzn1.dv.gti.[…]", "amzn1.dv.gti.[…]"]}]}
                for gti, lc in state['collections'].items():
                    for le in lc:
                        for e in le['titleIds']:
                            GTIs.append(e)
                            # Save parent/children relationships
                            parents[e] = gti
                            if not 'children' in self._videodata[gti]:
                                self._videodata[gti]['children'] = list()
                            if e not in self._videodata[gti]['children']:
                                self._videodata[gti]['children'].append(e)
                                bUpdated = True

            # Video info
            if 'detail' not in state:
                return bUpdated

            if urn not in self._videodata['urn2gti']:
                self._videodata['urn2gti'][urn] = state['pageTitleId']

            # Both of these versions have been spotted in the wild
            # { "detail": { … } }
            # { "detail": { "detail": {…}, "headerDetail": {…} } }
            details = state['detail']
            
            bMovie = False
            if 'headerDetail' in details and details['headerDetail'][state['pageTitleId']]['titleType'].lower() in ['movie', 'episode', 'unknown']:            
                #movies only need the header detail
                bMovie = True
                details = details['headerDetail']
            elif 'detail' in details:
                #series need the details inside detail
                details = details['detail']
                                      
            from json import dumps
            # Get details, seasons first
            for gti in sorted(details, key=lambda x: 'season' != details[x]['titleType']):
                item = details[gti]
                
                if (gti not in GTIs) and not bMovie:
                    #movies take header details an can continue, series not because take detail section inside of detail section and add items in wron place
                    continue
                
                if (oid not in details) and (gti not in GTIs):  # Most likely (surely?) movie
                    GTIs.append(gti)
                    o[gti] = {}
                if gti not in self._videodata:
                    self._videodata[gti] = {}
                vd = self._videodata[gti]
                                        
                item = details[gti]
                        
                #Log('details[gti][title]: {}'.format(details[gti]['title']))
                if (oid not in details) and (gti not in GTIs):  # Most likely (surely?) movie
                    GTIs.append(gti)
                    o[gti] = {}
                if gti not in self._videodata:
                    self._videodata[gti] = {}
                vd = self._videodata[gti]

                # Meta prep
                if 'metadata' not in vd:
                    vd['metadata'] = {'compactGTI': urn, 'artmeta': {}, 'videometa': {}}
                    bUpdate = True
                if 'artmeta' not in vd['metadata']:
                    vd['metadata']['artmeta'] = {}
                    bUpdate = True
                if 'videometa' not in vd['metadata']:
                    vd['metadata']['videometa'] = {}
                    bUpdate = True

                # Parent
                if gti in parents:
                    vd['parent'] = parents[gti]
                    bUpdate = True

                # Title
                if bCacheRefresh or ('title' not in vd):
                    if 'seasonNumber' not in item:
                        vd['title'] = self._BeautifyText(item['title'])
                    else:
                        try:
                            vd['title'] = state['strings']['AVOD_DP_season_selector'].format(seasonNumber=item['seasonNumber'])
                        except:
                            vd['title'] = 'Season {}'.format(item['seasonNumber'])
                    bUpdated = True

                # Images
                for k, v in {'thumb': 'packshot', 'poster': 'titleshot', 'fanart': 'heroshot'}.items():
                    if (bCacheRefresh or (k not in vd['metadata']['artmeta'])) and \
                       ('images' in item) and (v in item['images']) and item['images'][v]:
                        vd['metadata']['artmeta'][k] = item['images'][v]
                        bUpdated = True

                # Synopsis, media type, year, duration
                for k, v in {'plot': 'synopsis', 'mediatype': 'titleType', 'year': 'releaseYear', 'duration': 'duration'}.items():
                    if (bCacheRefresh or (k not in vd['metadata']['videometa'])) and (v in item):
                        vd['metadata']['videometa'][k] = item[v]
                        bUpdated = True

                # Genres
                if (bCacheRefresh or ('genre' not in vd['metadata']['videometa'])) and ('genres' in item) and item['genres']:
                    vd['metadata']['videometa']['genre'] = [g['text'] for g in item['genres']]
                    bUpdated = True

                # Premiered/Aired
                if (bCacheRefresh or ('premiered' not in vd['metadata']['videometa'])) and ('releaseDate' in item) and item['releaseDate']:
                    vd['metadata']['videometa']['premiered'] = DelocalizeDate(amzLang, item['releaseDate'])
                    vd['metadata']['videometa']['aired'] = vd['metadata']['videometa']['premiered']
                    bUpdated = True

                # MPAA
                if (bCacheRefresh or ('mpaa' not in vd['metadata']['videometa'])) and \
                   ('ratingBadge' in item) and ('displayText' in item['ratingBadge']) and item['ratingBadge']['displayText']:
                    vd['metadata']['videometa']['mpaa'] = item['ratingBadge']['displayText']
                    bUpdated = True

                # Contributors (`producers` are ignored)
                if 'contributors' in item:
                    for k, v in {'director': 'directors', 'cast': 'starringActors', 'cast': 'supportingActors'}.items():
                        if v in item['contributors']:
                            for p in item['contributors'][v]:
                                try:
                                    if (p['name'] not in vd['metadata']['videometa'][k]):
                                        vd['metadata']['videometa'][k].append(p['name'])
                                except KeyError:
                                    vd['metadata']['videometa'][k] = [p['name']]
                                bUpdated = True

                # Season, TV show title
                if ('seasonNumber' in item) and item['seasonNumber']:
                    if bCacheRefresh or ('season' not in vd['metadata']['videometa']):
                        vd['metadata']['videometa']['season'] = item['seasonNumber']
                        bUpdated = True
                    if bCacheRefresh or ('tvshowtitle' not in vd['metadata']['videometa']):
                        if 'parentTitle' in item:
                            vd['metadata']['videometa']['tvshowtitle'] = item['parentTitle']
                            bUpdated = True

                # Episode, Season, TV show title
                if ('episodeNumber' in item) and item['episodeNumber']:
                    if bCacheRefresh or ('episode' not in vd['metadata']['videometa']):
                        vd['metadata']['videometa']['episode'] = item['episodeNumber']
                        bUpdated = True
                    if bCacheRefresh or ('season' not in vd['metadata']['videometa']):
                        try:
                            vd['metadata']['videometa']['season'] = self._videodata[vd['parent']]['metadata']['videometa']['season']
                            bUpdated = True
                        except: pass
                    if bCacheRefresh or ('tvshowtitle' not in vd['metadata']['videometa']):
                        try:
                            vd['metadata']['videometa']['tvshowtitle'] = self._videodata[vd['parent']]['metadata']['videometa']['parentTitle']
                            bUpdated = True
                        except: pass

            # IMDB ratings — "imdb": {"amzn1.dv.gti.[…]": {"score": 8.5}}
            if ('imdb' in state) and state['imdb']:
                for gti in state['imdb']:
                    if (gti not in GTIs):
                        continue

                    if gti in self._videodata:
                        if not 'metadata' in self._videodata[gti]:
                            self._videodata[gti]['metadata'] = {'videometa' : {}}
                        vmd = self._videodata[gti]['metadata']['videometa']
                        if (bCacheRefresh or ('rating' not in vmd)) and ('score' in state['imdb'][gti]) and state['imdb'][gti]['score']:
                            vmd['rating'] = state['imdb'][gti]['score']
                            bUpdated = True

            # Trailer — "trailer": {"amzn1.dv.gti.[…]": {"playbackID": "amzn1.dv.gti.[…]", "playbackURL": "/detail/[ShortGTI]/ref=atv_dp_watch_trailer?autoplay=trailer"}}
            if ('trailer' in state) and state['trailer']:
                for gti in state['trailer']:
                    if gti in self._videodata:
                        if 'trailer' not in self._videodata[gti]:
                            self._videodata[gti]['trailer'] = True
                            bUpdated = True
                            
            if 'watchlist' in state and state['watchlist']:
                for gti, c in state['watchlist'].items():
                    if 'query' in c['endpoint']:
                        query = ''
                        query += '&'.join(['{}={}'.format(k, v) for k, v in c['endpoint']['query'].items()])
                        self._videodata[gti]['actions'] = [{'title': c['text']['string'],'url': '{0}?{1}'.format(c['endpoint']['partialURL'], query)}]
                        bUpdated = True
                            
            return bUpdated

        #### Lazyload Begin ####
        if 'lazyLoadURL' not in obj:
            return
        requestURLs = [obj['lazyLoadURL']]

        amzLang = None
        if None is not requestURLs[0]:
            # Find the locale amazon's using
            cj = MechanizeLogin()
            if cj:
                amzLang = cj.get('lc-main-av', path='/')
        amzLang = amzLang if amzLang else 'es_MX'

        bUpdatedVideoData = False  # Whether or not the pvData has been updated
        pageNumber = 1  # Page number

        #DEBUG
        sMainSection= ''
        bIsMenu = False
        if (len(requestURLs) > 0):
            sMainSection= requestURLs[0]
            #is in list menu (dont charge item info, only collections
            if sMainSection.startswith(u'/storefront/') or sMainSection.startswith(u'/watchlist/'):
                bIsMenu= True
            Log('Opening URL: {0} (Menu?: {1})'.format(sMainSection, bIsMenu), Log.DEBUG)

        while 0 < len(requestURLs):
            requestURL = requestURLs.pop(0)  # rULRs: FIFO stack
            o = obj

            # Load content
            bCouldNotParse = False
            try:
                cnt = None

                # Use cached data, if available
                if 'lazyLoadData' in o:
                    cnt = o['lazyLoadData']
                    del o['lazyLoadData']

                # Load content from an external url
                if not cnt:
                    urn = ExtractURN(requestURL)
                    if (not bCacheRefresh) and urn and (urn in self._videodata['urn2gti']):
                        # There are no API endpoints for movie/series pages, so we handle them in a separate function
                        bUpdatedVideoData |= ParseSinglePage(breadcrumb[-1], o, False, url=requestURL)
                        if 'lazyLoadURL' in o:
                            if 'ref' not in o:
                                o['ref'] = o['lazyLoadURL']
                            del o['lazyLoadURL']
                        continue
                    else:
                        cnt = self._GrabJSON(requestURL)
                        # from .logging import LogJSON
                        # LogJSON(cnt, requestURL)

                # Don't switch direct action for reference until we have content to show for it
                if cnt and ('lazyLoadURL' in o):
                    if 'ref' not in o:
                        o['ref'] = o['lazyLoadURL']
                    del o['lazyLoadURL']
            except:
                bCouldNotParse = True
            if bCouldNotParse or (not cnt):
                self._g.dialog.notification(getString(30251), requestURL, xbmcgui.NOTIFICATION_ERROR)
                Log('Unable to fetch the url: {}'.format(requestURL), Log.ERROR)
                continue
            
            #DEBUG
            Log('Load URL: {}'.format(requestURL), Log.DEBUG)
                        
            if bIsMenu:
                # Categories            
                if ('collections' in cnt):
                    for collection in cnt['collections']:
                        o[collection['webUid']] = {'title': self._BeautifyText(collection['text'])}
                        if ('facetImage' in collection):
                            sDescripcion= ''                                                                
                            if ('facetAlternateText' in collection):
                                if ('facetText' in collection):
                                    sDescription= '{0} {1}'.format(collection['facetText'], collection['facetAlternateText'])
                                else:
                                    sDescription=  collection['facetAlternateText']                                                                    
                            if 'facetImage' in collection:
                                sThumb = collection['facetImage']
                            else:
                                sThumb = ''                            
                            o[collection['webUid']] = {
                                'title': self._BeautifyText(collection['text']),
                                'lazyLoadURL': '/search/ref={}'.format(collection['webUid']),
                                'lazyLoadData': collection,
                                'metadata': {
                                    'artmeta': {
                                        'thumb': sThumb                                        
                                    },
                                    'videometa': {
                                        'mediatype': 'season',
                                        'plot': sDescription
                                    }
                                }
                            }
                            Log('facetImage Collection: {}'.format(collection['text']), Log.DEBUG)
                        elif 'seeMoreLink' in collection:
                            sThumb = ''
                            if 'facetImage' in collection:
                                sThumb = collection['facetImage']
                            o[collection['webUid']] = {
                                'title': self._BeautifyText(collection['text']),
                                #'lazyLoadURL': collection['seeMoreLink']['url'],
                                'lazyLoadURL': '/search/ref={}'.format(collection['webUid']),
                                'lazyLoadData': collection,
                                'metadata': {
                                    'artmeta': {
                                        'thumb': sThumb                                        
                                    },
                                    'videometa': {
                                        'mediatype': 'season',
                                        'plot': collection['seeMoreDescription']
                                    }
                                }
                            }
                            Log('SeeMoreLink Collection: {}'.format(collection['text']), Log.DEBUG)
                        
                        else:
                            Log('Other Collection: {}'.format(collection['text']), Log.DEBUG)
                            o[collection['webUid']] = {'title': collection['text']}  
                            o[collection['webUid']]['lazyLoadURL'] = requestURL
                            o[collection['webUid']]['lazyLoadData'] = collection
                else:
                    # Watchlist
                    if ('filters' in cnt):
                        for f in cnt['filters']:
                            # if it is not applied in all filters it indicates that it is the initial
                            if 'applied' not in cnt['filters'][len(cnt['filters'])-1]:
                                Log('Whatchlist menu: {}'.format(f['text']), Log.DEBUG)
                                o[f['id']] = {'title': f['text'], 'lazyLoadURL': f['apiUrl' if 'apiUrl' in f else 'href']}                 
                    else:
                        bIsMenu = False
                    
            if not bIsMenu:                      
                # Watchlist / Widow list / API Search
                #if ('items' in cnt) or (('content' in cnt) and ('items' in cnt['content'])):
                if ('items' in cnt):
                    for item in cnt['items']:                        
                        #Title
                        if 'heading' in item:
                            title = item['heading']
                        elif 'title' in item:
                            title = item['title']
                        else:
                            title = item['image']['alternateText']
                        #iu   
                        iu = ''
                        if 'href' in item:
                            iu = item['href']
                        elif 'link' in item:
                            iu = item['link']['url']
                            
                                            
                        if iu <> '':                       
                            #Image
                            if 'imageSrc' in item:
                                img = item['imageSrc'] 
                            elif 'image' in item and 'url' in item['image']:
                                img = item['image']['url']
                            else:
                                img = ''
                            #season
                            try:
                                t = item['watchlistAction']['endpoint']['query']['titleType'].lower()
                            except:
                                t = None
                                                    
                            if 'season' != t:
                                if (('title' in item) and ('watchlistAction' in item)) or ('heading' in item): #movie
                                    Log('Found Movie: {}'.format(title), Log.DEBUG)
                                    bUpdatedVideoData |= ParseSinglePage(breadcrumb[-1], o, bCacheRefresh, url=iu)
                                else: #channel
                                    Log('Found channel: {}'.format(title), Log.DEBUG)                
                                    bUpdatedVideoData |= AddChannel(breadcrumb[-1], o, title, img, iu)
                            else: #serie
                                Log('Found serie: {}'.format(title), Log.DEBUG)
                                bUpdatedVideoData |= AddSeason(breadcrumb[-1], o, title, img, iu)
                        else:  #LiveTV
                            #live channels only have playbackAction
                            if ('playbackAction' in item) and ('videoMaterialType' in item['playbackAction']) and (item['playbackAction']['videoMaterialType'].lower() ==  u'live'):
                                Log('Found Live TV: {}'.format(title), Log.DEBUG)                        
                                bUpdatedVideoData |= AddLiveChannel(breadcrumb[-1], item)
                            else:
                                log('unknown item content: {}'.format(item))                        
                else:
                    #Watchlist
                    if ('content' in cnt):
                        if 'items' in cnt['content']:
                            for item in cnt['content']['items']:
                                Log('Found watchlist item: {}'.format(item['title']), Log.DEBUG)
                                if item['watchlistAction']['endpoint']['query']['titleType'] == 'movie':
                                    bUpdatedVideoData |= ParseSinglePage(breadcrumb[-1], o, bCacheRefresh, url=item['href'])
                                else:
                                    bUpdatedVideoData |= AddSeason(breadcrumb[-1], o, item['title'], item['imageSrc'], item['href'])
                                                    
                    # Search/list
                    if ('results' in cnt) and ('items' in cnt['results']):
                        for item in cnt['results']['items']:
                            iu = item['title']['url']
                            if 'season' not in item:
                                Log('results: {}'.format(iu), Log.DEBUG)
                                bUpdatedVideoData |= ParseSinglePage(breadcrumb[-1], o, bCacheRefresh, url=iu)
                            else:
                                Log('results: {}'.format(item['title']['text']), Log.DEBUG)
                                bUpdatedVideoData |= AddSeason(breadcrumb[-1], o, item['title']['text'], MaxSize(item['packshot']['image']['src']), iu)

                    # Single page
                    if 'state' in cnt:
                        Log('state: {}'.format(cnt), Log.DEBUG)
                        bUpdatedVideoData |= ParseSinglePage(breadcrumb[-1], o, bCacheRefresh, data=cnt, url=requestURL)
                               
            # Pagination
            if 'pagination' in cnt:
                nextPage = None
                if 'apiUrl' in cnt['pagination']:
                    nextPage = cnt['pagination']['apiUrl']
                elif 'paginator' in cnt['pagination']:
                    nextPage = next((x['href'] for x in cnt['pagination']['paginator'] if
                                    (('type' in x) and ('NextPage' == x['type'])) or (('*className*' in x) and ('atv.wps.PaginatorNext' == x['*className*']))), None)
                if nextPage:
                    Log('Next page [{}]...'.format(pageNumber), Log.DEBUG)
                    requestURLs.append(nextPage)
                else:
                    Log('Unknown error while parsing pagination', Log.ERROR)

            # Notify new page
            if 0 < len(requestURLs):
                #update video data every 5 pages
                if (0 == (pageNumber % 5)) and bUpdatedVideoData:
                    self._Flush(bFlushCacheData=False, bFlushVideoData=True)
                    bUpdatedVideoData = False
                pageNumber += 1
                NotifyUser(getString(30252).format(pageNumber))
                
        # Flush catalog and data
        self._Flush(bFlushVideoData=bCacheRefresh or bUpdatedVideoData)
