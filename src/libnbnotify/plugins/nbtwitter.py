#-*- coding: utf-8 -*-
import libnbnotify
import twitter
import re
import hashlib
import urlparse
import os

PluginInfo = {'Requirements' : { 'OS' : 'All'}, 'API': 2, 'Authors': 'webnull', 'domain': '', 'type': 'extension', 'isPlugin': False, 'Description': 'Provides Twitter.com support'}

class PluginMain(libnbnotify.Plugin):
        api = ""

        def _pluginInit(self):
            print twitter
            self.api = twitter.Api()
            self.app.Hooking.connectHook("onAddPage", self.addPage)
            return True

        def addPage(self, data):
            link = data['link']

            match = re.findall("twitter\.com\/([A-Za-z0-9_\-\@ĄąŻżĘęŹźÓóŁł\$\#\&\;]+)", link)

            if len(match) == 0:
                return False

            userName = match[0]
            id = hashlib.md5(userName).hexdigest()

            return {'id': "twitter_"+str(match[0]), 'link': userName, 'extension': self, 'domain': 'www.dobreprogramy.pl', 'data': userName, 'dontDownload': True}

        def getAvatar(self, avatar):
            m = hashlib.md5(avatar).hexdigest()
            icon = self.app.iconCacheDir+"/"+m+".png"

            if not os.path.isfile(icon):
                parsedurl = urlparse.urlparse(avatar)
                data = self.app.httpGET(parsedurl.netloc, parsedurl.path)

                if data != False:
                    w = open(icon, "wb")
                    w.write(data)
                    w.close()
                    self.Logging.output("Avatar saved: "+avatar, "debug", False)
                else:
                    self.Logging.output("Cannot download avatar: "+avatar, "debug", False)
                    return ""
            
            return icon

        def checkComments(self, pageID, data):
            try:
                timeline = self.api.GetUserTimeline("webnull")
            except Exception:
                self.app.removePage(pageID)
                return False

            for event in timeline:
                title = str(event.user.name) + " @"+str(event.user.screen_name)+" ("+str(event.created_at)+")"
                avatar = self.getAvatar(str(event.user.profile_image_url))
                content = str(event.text)
                tweetid = "tweet_"+str(event.id)

                id = hashlib.md5(tweetid).hexdigest()

                if not id in self.app.pages[str(pageID)]['comments']:
                    self.app.pages[str(pageID)]['comments'][id] = {'avatar': avatar, 'username': title, 'content': content}
                    self.app.notifyNewData(content, title, avatar, pageID='')
                    self.app.addCommentToDB(pageID, id, avatar)















