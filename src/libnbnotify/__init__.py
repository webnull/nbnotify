from collections import defaultdict
import inspect, logging, traceback, os
from time import strftime, localtime
from StringIO import StringIO

class Logging:
    logger = None

    # -1 = Don't log any messages even important too
    # 0 = Don't log any messages, only if important (critical errors)
    # 1 = Log everything but debugging messages
    # 2 = Debug messages

    loggingLevel = 1 
    session = ""
    parent = None

    def __init__(self, Parent):
        self.parent = Parent
        self.initializeLogger()

    def convertMessage(self, message, stackPosition):
        return strftime("%d/%m/%Y %H:%M:%S", localtime())+", "+stackPosition+": "+message

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
        return True

    def output(self, message, utype='', savetoLogs=True, execHook=True, skipDate=False):
        """ Output to log file and to console """

        if not skipDate:
            message = self.convertMessage(message, inspect.stack()[1][3])
        
        if utype == "debug" and self.loggingLevel > 1:
            if self.logger is not None and savetoLogs:
                self.logger.debug(message)

            print(message)

        elif utype == "" and self.loggingLevel > 0:
            if self.logger is not None and savetoLogs:
                self.logger.info(message)

            print(message)

        elif utype == "warning" and self.loggingLevel > 0:
            if self.logger is not None and savetoLogs:
                self.logger.warning(message)

            print(message)

        elif utype == "critical" and self.loggingLevel > -1:
            if self.logger is not None and savetoLogs:
                self.logger.critical(message)

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
                    buffer = StringIO()
                    traceback.print_exc(file=buffer)
                    print(buffer.getvalue())

        return data       


class Plugin:
    app = None

    def __init__(self, app=None):
        self.app = app