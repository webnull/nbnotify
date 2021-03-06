from collections import defaultdict
import inspect, logging, traceback, os
from time import strftime, localtime
from StringIO import StringIO
import hashlib
import urlparse
import hashlib
import os
import time

class Notifications:
    """ Notifications queue system """

    _queue = dict()
    _m = False
    maxMessagesPerEvent = 3
    cached = list()

    app = None

    def cacheLoad(self):
        """ Load notifications cache """

        results = self.app.db.query("SELECT `sid`,`content` FROM `nb_notifications`;").fetchall()

        for i in results:
            #print("Appending "+i['content'])
            self.cached.append(i['sid'])

        return len(results)

    # check if already exists in cache
    def exists(self, sid):
        """ Check if Notification already exists in database """

        #sid = self.getSid(title, content, pageID, salt)

        if sid in self.cached:
            return True

        return False

    #def getSid(self, title, content, pageID, salt=''):
    #    return hashlib.md5(str(salt) + str(content) + str(pageID) + str(title)).hexdigest()


    ### Cache support
    def _cacheAdd(self, item):
        """ Add to cache """

        #if not "salt" in item:
        #    item['salt'] = ''

        #sid = self.getSid(item['title'], item['content'], item['pageID'], item['salt'])

        if item['sid'] == '':
            return False

        if item['sid'] in self.cached:
            return False

        #print("Adding to cache "+item['content'])

        self.cached.append(item['sid'])
        self.app.db.cursor.execute("INSERT INTO `nb_notifications` (sid, date, title, content, icon, pageID) VALUES (?, ?, ?, ?, ?, ?);", (item['sid'], item['date'], item['title'], item['content'], item['icon'], str(item['pageID'])))


    def __init__(self, app):
        self.app = app

        try:
            self.maxMessagesPerEvent = int(self.app.Config.getKey("global", "notifications_per_event", 3))
        except ValueError:
            self.maxMessagesPerEvent = 3

        if self.maxMessagesPerEvent < 1:
            self.maxMessagesPerEvent = 3

        self.app.Logging.output("Notification messages per event is "+str(self.maxMessagesPerEvent)+" (global->notifications_per_event)", "debug", False)

    def add(self, eventName, title, content, date, icon='', pageID='', sid='', testMode=False):
        """ Add new message to queue """

        self._m = True

        #self.app.Logging.output("Adding to queue of "+eventName, "debug", False)

        # create new event
        if not eventName in self._queue:
            self._queue[eventName] = list()

        item = {'date': date, 'title': title, 'content': content, 'icon': icon, 'pageID': pageID, 'sid': sid}

        # add to queue
        self._queue[eventName].append(item)

        # testMode is a good option for debugging notifications
        if testMode == False:
            self._cacheAdd(item)

        # remove first element from queue if its already full
        if len(self._queue[eventName]) > self.maxMessagesPerEvent:
            self._queue[eventName].pop(0)

        return True


    def sendMessages(self):
        """ Send all notifications """

        if self._m == False: # dont run if queue is unmodified
            return True

        for event in self._queue:
            for item in self._queue[event]:
                self.app.Hooking.executeHooks(self.app.Hooking.getAllHooks("onNotifyNewData"), [item['content'], item['title'], item['pageID'], item['icon']])
            
            self._queue[event] = list()

        #self.app.Logging.output("Notifications sent", "debug", False)
        self.app.Hooking.executeHooks(self.app.Hooking.getAllHooks("onSendMessages"), len(self._queue))

        self._m = False
        return True


class Logging:
    logger = None

    # -1 = Don't log any messages even important too
    # 0 = Don't log any messages, only if important (critical errors)
    # 1 = Log everything but debugging messages
    # 2 = Debug messages

    loggingLevel = 2
    session = ""
    silent = False
    parent = None
    logging = True

    def __init__(self, Parent):
        self.parent = Parent
        self.initializeLogger()

    def convertMessage(self, message, stackPosition):
        return strftime("%d/%m/%Y %H:%M:%S", localtime())+" "+stackPosition+": "+message

    def initializeLogger(self):
        try:
            if not os.path.isfile(os.path.expanduser("~/.nbnotify/nbnotify.log")):
                w = open(os.path.expanduser("~/.nbnotify/nbnotify.log"), "w")
                w.write(" ")
                w.close()

            self.logger = logging.getLogger('nbnotify')
            handler = logging.FileHandler(os.path.expanduser("~/.nbnotify/nbnotify.log"))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            return True
        except Exception as e:
            self.logger = None
            print("Cannot get access ~/.nbnotify/nbnotify.log, check your permissions. "+str(e))
        return False

    def turnOffLogger(self):
        self.logger = None
        self.logging = False
        return True

    def output(self, message, utype='', savetoLogs=True, execHook=True, skipDate=False):
        """ Output to log file and to console """

        if self.logging == False:
            return False

        if not skipDate:
            message = self.convertMessage(message, inspect.stack()[1][3])
        
        if utype == "debug" and self.loggingLevel > 1:
            if self.logger is not None and savetoLogs:
                self.logger.debug(message)

        elif utype == "" and self.loggingLevel > 0:
            if self.logger is not None and savetoLogs:
                self.logger.info(message)

        elif utype == "warning" and self.loggingLevel > 0:
            if self.logger is not None and savetoLogs:
                self.logger.warning(message)

        elif utype == "critical" and self.loggingLevel > -1:
            if self.logger is not None and savetoLogs:
                self.logger.critical(message)

        if self.silent == False:
            print(message)

        # save all messages to show in messages console
        self.session += message + "\n"

        # update console for example
        try:
            Hooks = self.parent.Hooking.getAllHooks("onLogChange")

            if Hooks:
                self.parent.Hooking.executeHooks(Hooks, self.session)

        except Exception as e:
            if execHook:
                self.parent.Logging.output(self.parent._("Error")+": "+self.parent._("Cannot execute hook")+"; onLogChange; "+str(e), "warning", True, False)
            else:
                print(self.parent._("Error")+": "+self.parent._("Cannot execute hook")+"; onLogChange; "+str(e))

class HookingException(Exception):
    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)

class Hooking:
    Hooks = defaultdict(list) # list of all hooks

    def connectHook(self, name, method):
        """ Connect to hook's socket """
        # defaultdict is used so if key doesn't exist it will be automaticly
        # created
        self.Hooks[name].append(method)

    def removeHook(self, name, method):
        if not name in self.Hooks:
            return True

        self.Hooks[name].remove(method)

        if len(self.Hooks[name]) == 0:
            del self.Hooks[name]

        return True

    def findClass(self, name, className):
        """ Search hook by class name """


        hooks = self.Hooks.get(name, False)

        for Hook in hooks:
            pluginName = str(Hook.im_class).replace("libnbnotify.plugins.", "").replace(".PluginMain", "")

            if pluginName == className:
                return Hook

        return False


    def getAllHooks(self, name):
        """ Get all hooked methods to execute them """
        return self.Hooks.get(name, False)


    def executeHooks(self, hooks, data=True):
        """ Executes all functions from list. Takes self.getAllHooks as hooks """

        if hooks:
            for Hook in hooks:
                try:
                    data = Hook(data)
                except Exception as e:
                    if str(e) == "pass": # request of a plugin to discontinue hooking
                        break

                    buffer = StringIO()
                    traceback.print_exc(file=buffer)
                    print(buffer.getvalue())

        return data       


class Plugin:
    app = None

    def __init__(self, app=None):
        self.app = app
        self.Logging = app.Logging

    def getPluginMethod(self, plugin):
        """ Get other plugin hooked object by class name """

        return self.app.Hooking.findClass("onAddPage", plugin)

    def shellquote(self, s):
        """ Escape shell command """

        return "'" + s.replace("'", "'\\''") + "'"

    def getPlugin(self, plugin):
        """ Get other plugin instance """

        if plugin in self.app.plugins:
            return self.app.plugins[plugin].instance

        return False


    def md5(self, data):
        return hashlib.md5(data).hexdigest()

    def getAvatar(self, avatar, id=False, imgType=False, cacheLifeTime=0):
        """ Simple local avatar cache
            Input: link to avatar image, optional alternative cache id
            Returns: path to cached local avatar image or nothing on error """

        avatar = avatar.replace('\/', '/')

        if id == False:
            m = self.md5(avatar)
        else:
            m = self.md5(id)

        if ".jpg" in avatar:
            icon = self.app.iconCacheDir+"/"+m+".jpg"
        else:
            icon = self.app.iconCacheDir+"/"+m+".png"

        if imgType != False:
            icon = self.app.iconCacheDir+"/"+m+"."+str(imgType)

        writeIcon = False

        # write new avatar
        if not os.path.isfile(icon):
            writeIcon = True
        else:
            if cacheLifeTime == 0:
                writeIcon = False
            else:
                if int(time.time())-int(os.path.getmtime(icon)) >= cacheLifeTime:
                    writeIcon = True


        if writeIcon == True:
            parsedurl = urlparse.urlparse(avatar)

            data = self.app.httpGET(parsedurl.netloc, parsedurl.path)

            if data != False and data != "":
                w = open(icon, "wb")
                w.write(data)
                w.close()
                self.Logging.output("Notify icon saved: "+avatar, "debug", False)
            else:
                self.Logging.output("Cannot get notify icon: "+avatar, "warning", True)
                return ""
        
        return icon

