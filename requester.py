import random
import requests
import string
import urllib

from Channel import *
from ChannelCategory import *
from ElementChannel import *
from ItemPlayableChannel import *
from ItemPlayableSeason import *
from SeasonEpisode import *

HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.89 Safari/537.36',
           'Content-Type': 'application/json'}
HEADERS_ENCODED = urllib.urlencode(HEADERS)
LOGIN_POST_DATA = '{"data":{},"action":"login","email":"%s","password":"%s","facebookParams":"","mobile":false,"hls":true,"flash":false,"isIframe":false,"login_type":"force","reminder":true,"conn_id":"%s"}'

USERNAME = ""
PASSWORD = ""

VVVVID_LOGIN_URL = "https://www.vvvvid.it/user/login"
VVVVID_KENC = "https://www.vvvvid.it/kenc?action=kt&"
VVVVID_BASE_URL = "https://www.vvvvid.it/vvvvid/ondemand/"
VVVVID_STATIC_URL = "https://static.vvvvid.it"
ANIME_CHANNELS_PATH = "anime/channels"
MOVIE_CHANNELS_PATH = "film/channels"
SHOW_CHANNELS_PATH = "show/channels"
ANIME_SINGLE_CHANNEL_PATH = "anime/channel/"
MOVIE_SINGLE_CHANNEL_PATH = "film/channel/"
SHOW_SINGLE_CHANNEL_PATH = "show/channel/"
ANIME_SINGLE_ELEMENT_CHANNEL_PATH = 'anime/'
SHOW_SINGLE_ELEMENT_CHANNEL_PATH = 'show/'
MOVIE_SINGLE_ELEMENT_CHANNEL_PATH = 'film/'

CHANNEL_MODE = "channel"
SINGLE_ELEMENT_CHANNEL_MODE = "elementchannel"
# plugin modes
MODE_MOVIES = '10'
MODE_ANIME = '20'
MODE_SHOWS = '30'

# parameter keys
PARAMETER_KEY_MODE = "mode"

# menu item names
ROOT_LABEL_MOVIES = "Movies"
ROOT_LABEL_ANIME = "Anime"
ROOT_LABEL_SHOWS = "Shows"

# episode stream type
F4M_TYPE = '10'
M3U_TYPE = '20'  # .m3u8 is the unicode version of .m3u

# session singleton
session = requests.Session()
session.headers.update(HEADERS)

conn_id = None


def getChannelsPath(type):
    if type == MODE_MOVIES:
        return MOVIE_CHANNELS_PATH
    elif type == MODE_ANIME:
        return ANIME_CHANNELS_PATH
    elif type == MODE_SHOWS:
        return SHOW_CHANNELS_PATH


def getSingleChannelPath(type):
    if type == MODE_MOVIES:
        return MOVIE_SINGLE_CHANNEL_PATH
    elif type == MODE_ANIME:
        return ANIME_SINGLE_CHANNEL_PATH
    elif type == MODE_SHOWS:
        return SHOW_SINGLE_CHANNEL_PATH


def get_section_channels(modeType):
    channelUrl = urllib.basejoin(VVVVID_BASE_URL, getChannelsPath(modeType))
    data = getJsonDataFromUrl(channelUrl)
    channels = data['data']
    listChannels = []
    for channelData in channels:
        filter = ''
        path = ''
        listCategory = []
        listFilters = []
        if 'filter' in channelData:
            for filter in channelData['filter']:
                listFilters.append(filter)
        if 'category' in channelData:
            for category in channelData['category']:
                channelCategoryElem = ChannelCategory(category['id'], category['name'])
                listCategory.append(channelCategoryElem)

        channel = Channel(unicode(channelData['id']), channelData['name'], listFilters, listCategory)
        listChannels.append(channel)
    return listChannels


def get_elements_from_channel(idChannel, type, idFilter='', idCategory=''):
    listElements = []
    middlePath = getSingleChannelPath(type)
    urlPostFix = '/last'
    while True:
        if idFilter != '':
            urlPostFix += '/?filter=' + idFilter
        elif idCategory != '':
            urlPostFix += '/?category=' + idCategory
        urlToLoad = urllib.basejoin(VVVVID_BASE_URL, middlePath + str(idChannel) + urlPostFix)
        data = getJsonDataFromUrl(urlToLoad)
        if 'data' not in data:
            break
        elements = data['data']
        for elementData in elements:
            elementData['thumbnail'] = urllib.basejoin(VVVVID_STATIC_URL, elementData['thumbnail']) + '|' + HEADERS_ENCODED
            elementChannel = ElementChannel(unicode(elementData['id']), unicode(elementData['show_id']),
                                            elementData['title'], elementData['thumbnail'],
                                            elementData['ondemand_type'], elementData['show_type'])
            listElements.append(elementChannel)
        urlPostFix = ''
    return listElements


def get_item_playable(idItem):
    urlToLoad = urllib.basejoin(VVVVID_BASE_URL, idItem + '/info')
    data = getJsonDataFromUrl(urlToLoad)
    info = data['data']
    itemPlayable = ItemPlayableChannel()
    itemPlayable.title = info['title']
    itemPlayable.thumb = urllib.basejoin(VVVVID_STATIC_URL, info['thumbnail']) + '|' + HEADERS_ENCODED
    itemPlayable.id = info['id']
    itemPlayable.show_id = info['show_id']
    itemPlayable.ondemand_type = info['ondemand_type']
    itemPlayable.show_type = info['show_type']
    itemPlayable = get_seasons_for_item(itemPlayable)
    return itemPlayable


def get_seasons_for_item(itemPlayable):
    urlToLoad = urllib.basejoin(VVVVID_BASE_URL, str(itemPlayable.show_id) + '/seasons')
    data = getJsonDataFromUrl(urlToLoad)
    result = data['data']
    itemPlayable.seasons = []
    for seasonData in result:
        season = ItemPlayableSeason()
        season.id = seasonData['show_id']
        season.show_id = seasonData['show_id']
        season.season_id = seasonData['season_id']
        if 'name' in seasonData:
            season.title = seasonData['name']
        else:
            season.title = itemPlayable.title
        urlToLoadSeason = urllib.basejoin(VVVVID_BASE_URL, str(itemPlayable.show_id) + '/season/' + str(season.season_id))
        dataSeason = getJsonDataFromUrl(urlToLoadSeason)
        resultSeason = dataSeason['data']
        listEpisode = []
        for episodeData in resultSeason:
            if episodeData['video_id'] != '-1':
                episode = SeasonEpisode()
                episode.show_id = season.show_id
                episode.season_id = season.season_id
                episode.stream_type = M3U_TYPE
                episodeData['embed_info'] = decode_embed_info(episodeData['embed_info'])
                if 'http' not in episodeData['embed_info']:
                    prefix = 'http://194.116.73.48/videomg/_definst_/mp4:'
                    postfix = '/playlist.m3u8'
                    episodeData['embed_info'] = episodeData['embed_info'].replace(' ', '%20')
                else:
                    prefix = ''
                    postfix = ''
                    if 'video/kenc' in episodeData['video_type']:
                        episodeData['embed_info'] = episodeData['embed_info'].replace('http', 'https')
                        kenc_data = getJsonDataFromUrl(VVVVID_KENC + urllib.urlencode({'url': episodeData['embed_info']}))
                        episodeData['embed_info'] += '?' + decode_embed_info(kenc_data['message'])
                episode.manifest = prefix + episodeData['embed_info'] + postfix + '|' + HEADERS_ENCODED
                episode.title = (episodeData['number'] + ' - ' + episodeData['title']).encode('utf-8', 'replace')
                episode.thumb = urllib.basejoin(VVVVID_STATIC_URL, episodeData['thumbnail']) + '|' + HEADERS_ENCODED
                listEpisode.append(episode)
        season.episodes = listEpisode
        itemPlayable.seasons.append(season)
    return itemPlayable


def getJsonDataFromUrl(customUrl):
    global conn_id
    if conn_id is None:
        conn_id = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))
        session.post(VVVVID_LOGIN_URL, data=LOGIN_POST_DATA % (USERNAME, PASSWORD, conn_id))

    if '?' in customUrl:
        customUrl += '&conn_id=%s' % conn_id
    else:
        customUrl += '?conn_id=%s' % conn_id

    response = session.get(customUrl)
    return response.json()


def decode_embed_info(h):
    def f(m):
        l = []
        o = 0
        b = False
        len_m = len(m)
        while not b and o < len_m:
            n = m[o] << 2
            o += 1
            k = -1
            j = -1
            if o < len_m:
                n += m[o] >> 4
                o += 1
                if o < len_m:
                    k = (m[o - 1] << 4) & 255
                    k += m[o] >> 2
                    o += 1
                    if o < len_m:
                        j = (m[o - 1] << 6) & 255
                        j += m[o]
                        o += 1
                    else:
                        b = True
                else:
                    b = True
            else:
                b = True
            l.append(n)
            if k != -1:
                l.append(k)
            if j != -1:
                l.append(j)
        return l

    g = 'MNOPIJKL89+/4567UVWXQRSTEFGHABCDcdefYZabstuvopqr0123wxyzklmnghij'
    c = [g.index(e) for e in h]
    len_c = len(c)
    e = len_c * 2 - 1
    while e >= 0:
        a = c[e % len_c] ^ c[(e + 1) % len_c]
        c[e % len_c] = a
        e -= 1
    c = f(c)
    d = ''.join([chr(e) for e in c])
    return d
