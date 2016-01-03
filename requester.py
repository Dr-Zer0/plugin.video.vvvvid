import requests

from Channel import *
from ChannelCategory import *
from ElementChannel import *
from ItemPlayableChannel import *
from ItemPlayableSeason import *
from SeasonEpisode import *

VVVVID_BASE_URL = "http://www.vvvvid.it/vvvvid/ondemand/"
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
session.headers.update({'User-Agent':
                            'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.14) Gecko/20080404 Firefox/2.0.0.14'})


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
    channelUrl = VVVVID_BASE_URL + getChannelsPath(modeType)
    data = getJsonDataFromUrl(channelUrl)
    channels = data['data']
    listChannels = []
    for channelData in channels:
        filter = ''
        path = ''
        listCategory = []
        listFilters = []
        if (channelData.has_key('filter')):
            for filter in channelData['filter']:
                listFilters.append(filter)
        if (channelData.has_key('category')):
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
        if (idFilter != ''):
            urlPostFix += '/?filter=' + idFilter
        elif (idCategory != ''):
            urlPostFix += '/?category=' + idCategory
        urlToLoad = VVVVID_BASE_URL + middlePath + str(idChannel) + urlPostFix
        data = getJsonDataFromUrl(urlToLoad)
        if 'data' not in data:
            break
        elements = data['data']
        for elementData in elements:
            elementChannel = ElementChannel(unicode(elementData['id']), unicode(elementData['show_id']),
                                            elementData['title'], elementData['thumbnail'],
                                            elementData['ondemand_type'], elementData['show_type'])
            listElements.append(elementChannel)
        urlPostFix = ''
    return listElements


def get_item_playable(idItem):
    urlToLoad = VVVVID_BASE_URL + idItem + '/info'
    data = getJsonDataFromUrl(urlToLoad)
    info = data['data']
    itemPlayable = ItemPlayableChannel()
    itemPlayable.title = info['title']
    itemPlayable.thumb = info['thumbnail']
    itemPlayable.id = info['id']
    itemPlayable.show_id = info['show_id']
    itemPlayable.ondemand_type = info['ondemand_type']
    itemPlayable.show_type = info['show_type']
    itemPlayable = get_seasons_for_item(itemPlayable)
    return itemPlayable


def get_seasons_for_item(itemPlayable):
    urlToLoad = VVVVID_BASE_URL + str(itemPlayable.show_id) + '/seasons'
    data = getJsonDataFromUrl(urlToLoad)
    result = data['data']
    itemPlayable.seasons = []
    for seasonData in result:
        season = ItemPlayableSeason()
        season.id = seasonData['show_id']
        season.show_id = seasonData['show_id']
        season.season_id = seasonData['season_id']
        if (seasonData.has_key('name')):
            season.title = seasonData['name']
        else:
            season.title = itemPlayable.title
        urlToLoadSeason = VVVVID_BASE_URL + str(itemPlayable.show_id) + '/season/' + str(season.season_id)
        dataSeason = getJsonDataFromUrl(urlToLoadSeason)
        resultSeason = dataSeason['data']
        listEpisode = []
        for episodeData in resultSeason:
            if (episodeData['video_id'] != '-1'):
                episode = SeasonEpisode()
                episode.show_id = season.show_id
                episode.season_id = season.season_id
                prefix = ''
                postfix = '?g=DRIEGSYPNOBI&hdcore=3.6.0&plugin=aasp-3.6.0.50.41'
                if ('http' not in episodeData['embed_info']):
                    episode.stream_type = M3U_TYPE
                    prefix = 'http://wowzaondemand.top-ix.org/videomg/_definst_/mp4:'
                    postfix = '/master.m3u8'
                if ('.m3u' in episodeData['embed_info']):
                    episode.stream_type = M3U_TYPE
                    prefix = ''
                    postfix = ''
                episode.manifest = prefix + episodeData['embed_info'] + postfix
                episode.title = ((episodeData['number'] + ' - ' + episodeData['title'])).encode('utf-8', 'replace')
                episode.thumb = episodeData['thumbnail']
                listEpisode.append(episode)
        season.episodes = listEpisode
        itemPlayable.seasons.append(season)
    return itemPlayable


def getJsonDataFromUrl(customUrl):
    response = session.get(customUrl)
    return response.json()
