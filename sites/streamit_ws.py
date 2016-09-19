# -*- coding: utf-8 -*-
from resources.lib.gui.gui import cGui
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.parser import cParser
from resources.lib import logger
from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.util import cUtil
from cCFScrape import cCFScrape
import re


SITE_IDENTIFIER = 'streamit_ws'
SITE_NAME = 'StreamIt'
SITE_ICON = 'streamit.png'

URL_MAIN = 'http://streamit.ws'
URL_SERIELINKS = 'http://streamit.ws/lade_episode.php'
URL_Kinofilme = URL_MAIN + '/kino'
URL_Filme = URL_MAIN + '/film'
URL_HDFilme = URL_MAIN + '/film-hd'
URL_SEARCH = URL_MAIN + '/suche/?s=%s'
URL_SERIES = URL_MAIN + '/serie'
URL_GENRES_FILM = URL_MAIN + '/genre-film'
URL_GENRES_SERIE = URL_MAIN + '/genre-serie'


def load():
    logger.info("Load %s" % SITE_NAME)
    oGui = cGui()
    params = ParameterHandler()

    params.setParam('sUrl', URL_Kinofilme)
    oGui.addFolder(cGuiElement('Kino Filme', SITE_IDENTIFIER, 'showEntries'), params)
    params.setParam('sUrl', URL_Filme)
    oGui.addFolder(cGuiElement('Neue Filme', SITE_IDENTIFIER, 'showEntries'), params)
    params.setParam('sUrl', URL_HDFilme)
    oGui.addFolder(cGuiElement('HD Filme', SITE_IDENTIFIER, 'showEntries'), params)
    params.setParam('sUrl', URL_GENRES_FILM)
    oGui.addFolder(cGuiElement('Genre Filme', SITE_IDENTIFIER, 'showGenre'), params)
    params.setParam('sUrl', URL_SERIES)
    oGui.addFolder(cGuiElement('Neue Serien', SITE_IDENTIFIER, 'showEntries'), params)
    params.setParam('sUrl', URL_GENRES_SERIE)
    oGui.addFolder(cGuiElement('Genre Serien', SITE_IDENTIFIER, 'showGenre'), params)
    oGui.addFolder(cGuiElement('Suche', SITE_IDENTIFIER, 'showSearch'))
    oGui.setEndOfDirectory()


def showGenre():
    oGui = cGui()
    params = ParameterHandler()
    entryUrl = params.getValue('sUrl')
    sHtmlContent = cRequestHandler(entryUrl).request()
    aResult = cParser().parse(sHtmlContent, '<h1>Genre.*?</h1>.*?</div>')

    if aResult[0]:
        sHtmlContent = aResult[1][0]

    pattern = '<li><a[^>]href="([^"]+)">([^"<]+)'  # url / title
    aResult = cParser().parse(sHtmlContent, pattern)

    for sUrl, sTitle in aResult[1]:
        params.setParam('sUrl', URL_MAIN + '/' + sUrl)
        oGui.addFolder(cGuiElement(cUtil().unescape(sTitle.decode('utf-8')).encode('utf-8'), SITE_IDENTIFIER, 'showEntries'), params)

    oGui.setEndOfDirectory()


def showEntries(entryUrl=False, sGui=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()

    if not entryUrl: entryUrl = params.getValue('sUrl')
    oRequestHandler = cRequestHandler(entryUrl)
    sHtmlContent = oRequestHandler.request()
    pattern = '<div class="cover"><a[^>]*href="([^"]+)" title="([^"]+).*?data-src="([^"]+)'
    aResult = cParser().parse(sHtmlContent, pattern)

    if not aResult[0]: 
        if not sGui: oGui.showInfo('xStream','Es wurde kein Eintrag gefunden')
        return

    total = len(aResult)
    for sUrl, sName, sThumbnail in aResult[1]:
        sFunction = "showHosters" if not "serie" in sUrl else "showSeasons"
        sThumbnail = cCFScrape().createUrl(URL_MAIN + sThumbnail, oRequestHandler)

        oGuiElement = cGuiElement(cUtil().unescape(sName.decode('utf-8')).encode('utf-8'), SITE_IDENTIFIER, sFunction)
        oGuiElement.setThumbnail(sThumbnail)
        oGuiElement.setMediaType('serie' if 'serie' in sUrl else 'movie')
        params.setParam('entryUrl', URL_MAIN + sUrl)
        params.setParam('sName', sName)
        params.setParam('Thumbnail', sThumbnail)
        oGui.addFolder(oGuiElement, params, bIsFolder="serie" in sUrl, iTotal=total)

    aResult = cParser().parse(sHtmlContent, '<a[^>]href=[^>]([^">]+)[^>]>Next')
    if aResult[0] and aResult[1][0]:
        params.setParam('sUrl', entryUrl + aResult[1][0])
        oGui.addNextPage(SITE_IDENTIFIER, 'showEntries', params)

    if not sGui:
        oGui.setView('tvshows' if 'serie' in entryUrl else 'movies')
        oGui.setEndOfDirectory()

def showSeasons():
    oGui = cGui()
    oParams = ParameterHandler()

    sUrl = oParams.getValue('entryUrl')
    sThumbnail = oParams.getValue("Thumbnail")
    sName = oParams.getValue('sName')
    sHtmlContent = cRequestHandler(sUrl).request()

    sPattern = '<select[^>]*class="staffelauswahl"[^>]*>(.*?)</select>' # container
    aResult = cParser().parse(sHtmlContent, sPattern)

    if aResult[0]: 
        sPattern = '<option[^>]*value="(.*?)"[^>]*>(.*?)</option>' # container
        aResult = cParser().parse(aResult[1][0], sPattern)

    if not aResult[0]: 
        if not sGui: oGui.showInfo('xStream','Es wurde kein Eintrag gefunden')
        return

    total = len(aResult[1])
    for iSeason, sTitle in aResult[1]:
        oGuiElement = cGuiElement("Staffel " + str(iSeason),SITE_IDENTIFIER, 'showEpisodes')
        oGuiElement.setTVShowTitle(sName)
        oGuiElement.setSeason(iSeason)
        oGuiElement.setMediaType('season')
        oGuiElement.setThumbnail(sThumbnail)
        oGui.addFolder(oGuiElement, oParams, iTotal = total)

    oGui.setView('seasons')
    oGui.setEndOfDirectory()

def showEpisodes():
    oGui = cGui()
    oParams = ParameterHandler()

    sUrl = oParams.getValue('entryUrl')
    sThumbnail = oParams.getValue("Thumbnail")
    sSeason = oParams.getValue('season')
    sShowName = oParams.getValue('TVShowTitle')
    sHtmlContent = cRequestHandler(sUrl).request()

    parser = cParser()
    sPattern = '<a[^>]*href="#(s%se(\d+))"[^>]*>(.*?)</a>' % sSeason
    aResult = parser.parse(sHtmlContent, sPattern)

    if not aResult[0]: 
        oGui.showInfo('xStream','Es wurde kein Eintrag gefunden')
        return

    result, imdb = parser.parseSingleResult(sHtmlContent,'IMDB\s?=\s?\'(\d+)')
    
    total = len(aResult[1])
    for sEpisodeUrl, sEpisodeNr, sEpisodeTitle in aResult[1]:
        res = re.search('%s (.*)' % sEpisodeNr, sEpisodeTitle)
        if res:
            sEpisodeTitle = '%s - %s' % (sEpisodeNr, res.group(1))
        oGuiElement = cGuiElement(sEpisodeTitle, SITE_IDENTIFIER, "showHosters")
        oGuiElement.setThumbnail(sThumbnail)
        oGuiElement.setTVShowTitle(sShowName)
        oGuiElement.setEpisode(sEpisodeNr)
        oGuiElement.setSeason(sSeason)
        oGuiElement.setMediaType('episode')
        oParams.setParam('entryUrl', sUrl)
        oParams.setParam('val', sEpisodeUrl)
        oParams.setParam('IMDB', imdb)
        oGui.addFolder(oGuiElement, oParams, bIsFolder=False, iTotal=total)

    oGui.setView('episodes')
    oGui.setEndOfDirectory()

def showHosters():
    oParams = ParameterHandler()
    sUrl = oParams.getValue('entryUrl')
    oRequestHandler = cRequestHandler(sUrl)

    if oParams.getValue('val'):
        oRequestHandler = cRequestHandler(URL_SERIELINKS)
        oRequestHandler.addParameters('val', oParams.getValue('val'))
        oRequestHandler.addParameters('IMDB', oParams.getValue('IMDB'))
        oRequestHandler.setRequestType(1)

    sHtmlContent = oRequestHandler.request()
    aResult = cParser().parse(sHtmlContent, '<div[^>]class="mirrors.*?<div[^>]id="content">')  # filter main content if needed

    if aResult[0]:
        sHtmlContent = aResult[1][0]

    sPattern = '<a href="([^"]+).*?name="save"[^>]value="(.*?)"'  # url / hostername
    aResult = cParser().parse(sHtmlContent, sPattern)
    hosters = []
    if aResult[1]:
        for sUrl, sName in aResult[1]:
            oRequestHandler = cRequestHandler(sUrl)
            sHtmlContent = oRequestHandler.request()
            Pattern = 'none"><a[^>]*href="([^"]+)'
            bResult = cParser().parse(sHtmlContent, Pattern)
            if bResult[1]:
                for Url in bResult[1]:
                    hoster = {}
                    hoster['name'] = sName.strip()
                    hoster['link'] = Url
                    hosters.append(hoster)

    if hosters:
        hosters.append('getHosterUrl')

    return hosters


def getHosterUrl(sUrl=False):
    if not sUrl: sUrl = ParameterHandler().getValue('url')
    results = []
    result = {}
    result['streamUrl'] = sUrl
    result['resolved'] = False
    results.append(result)
    return results


def showSearch():
    oGui = cGui()
    sSearchText = oGui.showKeyBoard()
    if not sSearchText: return
    _search(False, sSearchText)
    oGui.setEndOfDirectory()


def _search(oGui, sSearchText):
    if not sSearchText: return
    showEntries(URL_SEARCH % sSearchText.strip(), oGui)