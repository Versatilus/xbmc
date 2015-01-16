#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import time
import urllib
import demjson
import xbmcplugin
import xbmc
import xbmcgui
import subprocess
import os
import resources.lib.common as common

from BeautifulSoup import BeautifulStoneSoup
from BeautifulSoup import BeautifulSoup
try:
    from xml.etree import ElementTree
except:
    from elementtree import ElementTree

pluginhandle = common.pluginhandle

def GETSUBTITLES(values):
    getsubs  = 'https://atv-ps-eu.amazon.com/cdp/catalog/GetSubtitleUrls'
    getsubs += '?NumberOfResults=1'
    getsubs += '&firmware=WIN%2016,0,0,235%20PlugIn'
    getsubs += '&deviceTypeID='+values['deviceTypeID']
    getsubs += '&customerID='+values['customerID']
    getsubs += '&deviceID='+values['deviceID']
    getsubs += '&format=json'
    getsubs += '&asin='+values['asin']
    getsubs += '&version=2'
    getsubs += '&token='+values['token']
    getsubs += '&videoType=content'
    data = common.getURL(getsubs,'atv-ps-eu.amazon.com',useCookie=True)
    subtitleLanguages = demjson.decode(data)['message']['body']['subtitles']['content']['languages']
    if len(subtitleLanguages) > 0:
        subtitleUrl = subtitleLanguages[0]['url']
        subtitles = CONVERTSUBTITLES(subtitleUrl)
        common.SaveFile(os.path.join(common.pluginpath,'resources','cache',values['asin']+'.srt'), subtitles)

def CONVERTSUBTITLES(url):
    xml=common.getURL(url)
    tree = BeautifulStoneSoup(xml, convertEntities=BeautifulStoneSoup.XML_ENTITIES)
    lines = tree.find('tt:body').findAll('tt:p')
    stripTags = re.compile(r'<.*?>',re.DOTALL)
    spaces = re.compile(r'\s\s\s+')
    srt_output = ''
    count = 1
    displaycount = 1
    for line in lines:
        sub = line.renderContents()
        sub = stripTags.sub(' ', sub)
        sub = spaces.sub(' ', sub)
        sub = sub.decode('utf-8')
        start = line['begin'].replace('.',',')
        if count < len(lines):
            end = line['end'].replace('.',',')
        line = str(displaycount)+"\n"+start+" --> "+end+"\n"+sub+"\n\n"
        srt_output += line
        count += 1
        displaycount += 1
    return srt_output.encode('utf-8')

def SETSUBTITLES(asin):
    subtitles = os.path.join(common.pluginpath,'resources','cache',asin+'.srt')
    if os.path.isfile(subtitles) and xbmc.Player().isPlaying():
        print "AMAZON --> Subtitles Enabled."
        xbmc.Player().setSubtitles(subtitles)
    elif xbmc.Player().isPlaying():
        print "AMAZON --> Subtitles File Available."
    else:
        print "AMAZON --> No Media Playing. Subtitles Not Assigned."

def GETTRAILERS(getstream):
    data = common.getURL(getstream,'atv-ps-eu.amazon.com')
    rtmpdata = demjson.decode(data)
    if rtmpdata['message']['statusCode'] == "SUCCESS":
        sessionId = rtmpdata['message']['body']['streamingURLInfoSet']['sessionId']
        cdn = rtmpdata['message']['body']['streamingURLInfoSet']['cdn']
        rtmpurls = rtmpdata['message']['body']['streamingURLInfoSet']['streamingURLInfo']
        title = rtmpdata['message']['body']['metadata']['title'].replace('[HD]','')
        return rtmpurls, sessionId, cdn, title
    else:
        return False, False, False

def PLAYTRAILER_RESOLVE():
    PLAYTRAILER(resolve=True)

def PLAYTRAILER(resolve=False):
    swfUrl, values, owned = GETFLASHVARS(common.args.url) 
    values['deviceID'] = values['customerID'] + str(int(time.time() * 1000)) + values['asin']
    getstream  = 'https://atv-ps-eu.amazon.com/cdp/catalog/GetStreamingTrailerUrls'
    getstream += '?asin='+values['asin']
    getstream += '&deviceTypeID='+values['deviceTypeID']
    getstream += '&deviceID='+values['deviceID']
    getstream += '&firmware=WIN%2016,0,0,235%20PlugIn'
    getstream += '&format=json'
    getstream += '&version=1'
    rtmpurls, streamSessionID, cdn, videoname = GETTRAILERS(getstream)
    if rtmpurls == False:
        xbmcgui.Dialog().ok('Kein Trailer verfügbar','')
    elif cdn == 'limelight':
        xbmcgui.Dialog().ok('Limelight CDN','Limelight uses swfverfiy2. Playback may fail.')
    else:
        PLAY(rtmpurls,swfUrl=swfUrl,Trailer=videoname,resolve=resolve)
        
def GETSTREAMS(getstream):
    data = common.getURL(getstream,'atv-ps-eu.amazon.com',useCookie=True)
    rtmpdata = demjson.decode(data)
    if rtmpdata['message']['statusCode'] != "SUCCESS":
        return False, False, rtmpdata['message']['statusCode'], rtmpdata['message']['body']['code']
       
    drm = rtmpdata['message']['body']['urlSets']['streamingURLInfoSet'][0]['drm']
    if drm <> 'NONE':
        xbmcgui.Dialog().ok('DRM Detected','This video uses %s DRM' % drm)

    sessionId = rtmpdata['message']['body']['urlSets']['streamingURLInfoSet'][0]['sessionId']
    cdn = rtmpdata['message']['body']['urlSets']['streamingURLInfoSet'][0]['cdn']
    rtmpurls = rtmpdata['message']['body']['urlSets']['streamingURLInfoSet'][0]['streamingURLInfo']
    title = rtmpdata['message']['body']['metadata']['title'].replace('[HD]','')
    return rtmpurls, sessionId, cdn, title


def PLAYVIDEO():
    if not os.path.isfile(common.COOKIEFILE):
        common.mechanizeLogin()
    swfUrl, values, owned = GETFLASHVARS(common.args.url)

    values['deviceID'] = values['customerID'] + str(int(time.time() * 1000)) + values['asin']
    
    if common.addon.getSetting("enable_captions")=='true':
        GETSUBTITLES(values)
    getstream  = 'https://atv-ps-eu.amazon.com/cdp/catalog/GetStreamingUrlSets'
    getstream += '?asin='+values['asin']
    getstream += '&deviceTypeID='+values['deviceTypeID']
    getstream += '&firmware=WIN%2016,0,0,235%20PlugIn'
    getstream += '&customerID='+values['customerID']
    getstream += '&deviceID='+values['deviceID']
    getstream += '&token='+values['token']
    getstream += '&format=json'
    getstream += '&version=1'
    
    rtmpurls, streamSessionID, cdn, title = GETSTREAMS(getstream)
    if not rtmpurls:
        xbmcgui.Dialog().ok("Fehler beim Laden, bitte Datenbank aktualisieren\n%s: %s" % (cdn,title), "Amazon")
        return PLAYTRAILER_RESOLVE()
    if cdn == 'limelight':
        xbmcgui.Dialog().ok('Limelight CDN','Limelight uses swfverfiy2. Playback may fail.')
    if rtmpurls <> False:
        basertmp, ip = PLAY(rtmpurls,swfUrl=swfUrl,title=title)
        if not basertmp: return
    if streamSessionID <> False:
        epoch = str(int(time.mktime(time.gmtime()))*1000)
        USurl =  'https://atv-ps-eu.amazon.com/cdp/usage/UpdateStream'
        USurl += '?device_type_id='+values['deviceTypeID']
        USurl += '&deviceTypeID='+values['deviceTypeID']
        USurl += '&streaming_session_id='+streamSessionID
        USurl += '&operating_system='
        USurl += '&timecode=45.003'
        USurl += '&flash_version=WIN%2016,0,0,235%20PlugIn'
        USurl += '&asin='+values['asin']
        USurl += '&token='+values['token']
        USurl += '&browser='+urllib.quote_plus(values['userAgent'])
        USurl += '&server_id='+ip
        USurl += '&client_version='+swfUrl.split('/')[-2]
        USurl += '&unique_browser_id='+values['UBID']
        USurl += '&device_id='+values['deviceID']
        USurl += '&format=json'
        USurl += '&version=1'
        USurl += '&page_type='+values['pageType']
        USurl += '&start_state=Video'
        USurl += '&amazon_session_id='+values['sessionID']
        USurl += '&event=STOP'
        USurl += '&firmware=WIN%2016,0,0,235%20PlugIn'
        USurl += '&customerID='+values['customerID']
        USurl += '&deviceID='+values['deviceID']
        USurl += '&source_system=http://www.amazon.de'
        USurl += '&http_referer=ecx.images-amazon.com'
        USurl += '&event_timestamp='+epoch
        USurl += '&encrypted_customer_id='+values['customerID']

        epoch = str(int(time.mktime(time.gmtime()))*1000)
        surl =  'https://atv-ps-eu.amazon.com/cdp/usage/ReportStopStreamEvent'
        surl += '?deviceID='+values['deviceID']
        surl += '&source_system=http://www.amazon.de'
        surl += '&format=json'
        surl += '&event_timestamp='+epoch
        surl += '&encrypted_customer_id='+values['customerID']
        surl += '&http_referer=ecx.images-amazon.com'
        surl += '&device_type_id='+values['deviceTypeID']
        surl += '&download_bandwidth=9926.295518207282'
        surl += '&device_id='+values['deviceTypeID']
        surl += '&from_mode=purchased'
        surl += '&operating_system='
        surl += '&version=1'
        surl += '&flash_version=WIN%2016,0,0,235%20PlugIn'
        surl += '&url='+urllib.quote_plus(basertmp)
        surl += '&streaming_session_id='+streamSessionID
        surl += '&browser='+urllib.quote_plus(values['userAgent'])
        surl += '&server_id='+ip
        surl += '&client_version='+swfUrl.split('/')[-2]
        surl += '&unique_browser_id='+values['UBID']
        surl += '&amazon_session_id='+values['sessionID']
        surl += '&page_type='+values['pageType']
        surl += '&start_state=Video'
        surl += '&token='+values['token']
        surl += '&to_timecode=3883'
        surl += '&streaming_bit_rate=348'
        surl += '&new_streaming_bit_rate=2500'
        surl += '&asin='+values['asin']
        surl += '&deviceTypeID='+values['deviceTypeID']
        surl += '&firmware=WIN%2016,0,0,235%20PlugIn'
        surl += '&customerID='+values['customerID']
                
        """if values['pageType'] == 'movie':
            import movies as moviesDB
            moviesDB.watchMoviedb(values['asin'])
        if values['pageType'] == 'tv':
            import tv as tvDB
            tvDB.watchEpisodedb(values['asin'])
        """    
        if common.addon.getSetting("enable_captions")=='true':
            while not xbmc.Player().isPlaying():
                xbmc.sleep(100)
            SETSUBTITLES(values['asin'])
            
def GETFLASHVARS(pageurl):
    swfUrl = ''
    showpage = common.getURL(pageurl,useCookie=True)
    #print showpage
    flashVars = re.compile('var config = {"general":{(.*?)}.*"fl_config":{"initParams":{(.*?)}(.*?){',re.DOTALL).findall(showpage)
    flashVars =(flashVars[0][0] + flashVars[0][1] + flashVars[0][2]).split(',')

    values={'token'          :'',
            'deviceTypeID'   :'A13Q6A55DBZB7M',
            #'deviceTypeID'   :'A324MFXUEZFF7B', # GoogleTV
            'version'        :'1',
            'firmware'       :'1',       
            'customerID'     :'',
            'format'         :'json',
            'deviceID'       :'',
            'asin'           :''      
            }
    if '<div class="avod-post-purchase">' in showpage:
        owned=True
    else:
        owned=False
    for item in flashVars:
        item = item.replace('"','').split(':',1)
        if item[0]      == 'csrfToken':
            values['token']         = 'bba9a4216cd8ec5afea664f2b9a8319c'
        elif item[0]    == 'customer':
            values['customerID']    = item[1]
        elif item[0]    == 'ASIN':
            values['asin']          = item[1]
        elif item[0]    == 'pageType':
            values['pageType']      = item[1]        
        elif item[0]    == 'UBID':
            values['UBID']          = item[1]
        elif item[0]    == 'sessionID':
            values['sessionID']     = item[1]
        elif item[0]    == 'userAgent':
            values['userAgent']     = item[1]
            #values['userAgent']     = "GoogleTV 162671"
        elif item[0]    == 'playerSwf':
            swfUrl                  = item[1]
    return swfUrl, values, owned
        
def PLAY(rtmpurls,swfUrl,Trailer=False,resolve=True,title=False):
    lbitrate = int(common.addon.getSetting("bitrate"))
    mbitrate = 0
    streams = []
    for data in rtmpurls:
        url = data['url']
        bitrate = float(data['bitrate'])
        videoquality = data['contentQuality']
        audioquality = data['audioCodec']
        formatsplit = re.compile("_video_([^_]*)_.*_audio_([^_]*)_([0-9a-zA-Z]*)").findall(url)
        try:
            videoquality += ' ' + formatsplit[0][0]
            audioquality += ' ' + formatsplit[0][2]
        except: pass
        if lbitrate == 0:
            streams.append([bitrate,url,videoquality,audioquality])
        elif bitrate >= mbitrate and bitrate <= lbitrate:
            mbitrate = bitrate
            rtmpurl = url

    if lbitrate == 0:
        streamsout = []
        for stream in streams:
            if stream[0] > 999: 
                streamsout.append(str(stream[0]/1000)+' Mbps - '+stream[2]+', '+stream[3])
            else: 
                streamsout.append(str(int(stream[0]))+' Kbps - '+stream[2]+', '+stream[3])
        quality=xbmcgui.Dialog().select('Stream Qualität auswählen:', streamsout)
        if quality!=-1:
            mbitrate = streams[quality][0]
            rtmpurl = streams[quality][1]
        else:
            return False, False
    
    cachesize = int(20 * mbitrate / 8) # 20 sec cache
    print "bitrate: %s   cache: %s" % (mbitrate, cachesize)
    
    rtmpurlSplit = re.compile("([^:]*):\/\/([^\/]+)\/([^\/]+)\/([^\?]+)(\?.*)?").findall(rtmpurl)[0]
    protocol = rtmpurlSplit[0]
    hostname = rtmpurlSplit[1]
    appName =  rtmpurlSplit[2]
    stream = rtmpurlSplit[3]
    auth = rtmpurlSplit[4]
        
    basertmp = 'rtmp://'+hostname+'/'+appName

    if 'edgefcs' in hostname:
        basertmp += auth
    else:
        stream += auth

    if Trailer and not resolve:
        finalname = 'Trailer - ' + Trailer
    else:
        finalname = title
    
    finalUrl = '%s app=%s swfUrl=%s pageUrl=%s playpath=%s swfVfy=true' % (basertmp, appName, swfUrl, common.args.url, stream)
    item = xbmcgui.ListItem(finalname,path=finalUrl)
    item.setInfo( type="Video", infoLabels={ "Title": finalname})
    item.setProperty('IsPlayable', 'true')
    xbmc.Player().play(finalUrl, item)

    return basertmp, hostname