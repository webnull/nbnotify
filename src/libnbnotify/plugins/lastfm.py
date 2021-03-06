#-*- coding: utf-8 -*-
import libnbnotify
import re
import hashlib
import urlparse
import os
import json
import datetime
#import time

PluginInfo = {'Requirements' : { 'OS' : 'All'}, 'API': 2, 'Authors': 'webnull', 'domain': '', 'type': 'extension', 'isPlugin': True, 'Description': 'Tracking last played music by last.fm user'}

class PluginMain(libnbnotify.Plugin):
        """ Watch lastfm user's last played tracks """

        api_key = "000a9f703923c78d3f7b412a90e784d9"
        link = "/2.0/?method={$method}&user={$user}&api_key={$api_key}&format=json"

        def _pluginInit(self):
            self.app.Hooking.connectHook("onAddPage", self.addPage)
            return True

        def addPage(self, data):
            link = data['link']

            match = re.findall("lastfm\.([a-z]+)\/user\/([A-Za-z0-9_\-\@ĄąŻżĘęŹźÓóŁł\$\#\&\;]+)", link)

            if len(match) == 0:
                return False

            userName = match[0][1]
            id = hashlib.md5(userName).hexdigest()

            return {'id': "lastfm_"+userName, 'link': self.link.replace("{$user}", userName).replace("{$api_key}", self.api_key).replace("{$method}", "user.getrecenttracks"), 'extension': self, 'domain': 'ws.audioscrobbler.com', 'data': userName}

        def getAvatar(self, avatar):
            avatar = avatar.replace('\/', '/')

            m = hashlib.md5(avatar).hexdigest()

            if ".jpg" in avatar:
                icon = self.app.iconCacheDir+"/"+m+".jpg"
            else:
                icon = self.app.iconCacheDir+"/"+m+".png"

            if not os.path.isfile(icon):
                parsedurl = urlparse.urlparse(avatar)
                data = self.app.httpGET(parsedurl.netloc, parsedurl.path)

                if data != False:
                    w = open(icon, "wb")
                    w.write(data)
                    w.close()
                    self.Logging.output("lastfm avatar saved: "+avatar, "debug", False)
                else:
                    self.Logging.output("Cannot download avatar from lastfm: "+avatar, "warning", True)
                    return ""
            
            return icon

        def checkComments(self, pageID, data):
            t = json.loads(data)

            self.Logging.output("Last.fm API check: "+str(t['recenttracks']['@attr']['user']), "debug", False)

            t['recenttracks']['track'].reverse()
            i = 0

            for track in t['recenttracks']['track']:
                i = i + 1

                if i > self.app.Notifications.maxMessagesPerEvent and self.app.Notifications.maxMessagesPerEvent > 0:
                    break

                played = track['artist']['#text'] + " - " + track['name']

                # unique ID based on lastfm's track id + playing date
                try:
                    if track['@attr']['nowplaying']:
                        date = datetime.datetime.today().strftime("%d %b %Y, %H:%M")
                except Exception as e:
                    date = track['date']['#text']

                #date = int(time.time())
                template = "{$track}\n{$date}"

                try:
                    if track['@attr']['nowplaying']:
                        template = "Playing now:\n{$track}"
                except Exception as e:
                    pass

                message = template.replace("{$track}", played)

                try:
                    message = message.replace("{$date}", track['date']['#text'])
                except Exception:
                    message = message.replace("{$date}", "")

                title = t['recenttracks']['@attr']['user'] + " @ last.fm"

                sid = hashlib.md5(date+message).hexdigest()

                if self.app.Notifications.exists(sid) == False:
                    avatar = self.getAvatar(str(track['image'][1]['#text']))

                    #self.app.notifyNewData(str(message), title, avatar)
                    self.app.Notifications.add('lastfm_'+t['recenttracks']['@attr']['user'], title, message, '', avatar, pageID, sid=sid)
                

