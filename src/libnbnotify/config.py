import sys
import os
import copy

if sys.version_info[0] >= 3:
    import configparser
else:
    import ConfigParser as configparser


class Config:
    """ Configuration manager, basing on ini configuration files """

    Config = dict()
    configTime = None # config last modification time
    app = None

    def __init__(self, app, file):
        self.file = file
        self.app = app
        self.Config = dict()

    def __str__(self):
        return str(self.Config)
        

    def setKey(self, Section, Option, Value):
        """ Set configuration key """

        if not Section in self.Config:
            self.Config[Section] = dict()

        self.Config[Section][Option] = str(Value)

        return True

    def renameAllKeys(self, key, newName):
        if key == newName:
            return True

        c = copy.deepcopy(dict(self.Config))

        for s in c:
            for k in c[s]:
                if k == key:
                    value = self.Config[s][k]

                    self.Config[s].pop(k)
                    self.Config[s][newName] = value
        return True


    def removeKey(self, Section, Option):
        try:
            return self.Config[Section].pop(Option)
        except KeyError:
            self.app.Logging.output("KeyError in "+Section+"->"+Option, "debug", False)
            return False
    

    def getSection(self, Section):
        """ Returns section as dictionary 

            Args:
              Section - name of section of ini file ([section] header)

            Returns:
              Dictionary - on success
              False - on false

        """
        return self.Config.get(Section, False)


    def getKey(self, Section, Key, default=None):
        """ Returns value of Section->Value configuration variable

            Args:
              Section - name of section of ini file ([section] header)
              Key - variable name

            Returns:
              False - when section or key does not exists
              False - when value of variable is "false" or "False" or just False
              string value - value of variable
        """

        try:
            cfg = self.Config[Section][Key]

            # returning int values instead of strings
            try:
                cfg = int(cfg)
            except ValueError:
                pass

            if str(cfg).lower() == "false":
                return False
            else:
                return cfg

        except KeyError:
            # if we specified default value, let it be saved to configuration file too
            if default != None:
                self.app.Logging.output("Default configuration key set: "+Section+" => "+Key+" = "+str(default), "debug", True)
                self.setKey(Section, Key, default)
                self.save()
                return default

            return False

    def checkChanges(self):
        if os.path.getmtime(self.file) != self.configTime:
            self.app.Logging.output("Reloading configuration...", "debug", False)
            self.loadConfig()
            self.app.addPagesFromConfig()
            return True


    def save(self):
        """ Save configuration to file """

        Output = ""
        r = False

        # saving settings to file
        for Section in self.Config:
            Output += "["+str(Section)+"]\n"

            for Option in self.Config[Section]:
                Output += str(Option)+" = "+str(self.Config[Section][Option])+"\n"

            Output += "\n"

        try:
            self.app.Logging.output("Saving to "+self.file, "debug", True)
            Handler = open(self.file, "wb")
            Handler.write(Output)
            Handler.close()
            r = True
        except Exception as e:
            print("Cannot save configuration to file "+self.file)
            r = False

        self.configTime = os.path.getmtime(self.file)
        return r

    def loadConfig(self):
        """ Parsing configuration ini file """

        self.app.Logging.output("Parsing "+self.file, "debug", False)

        if os.path.isfile(self.file):
            Parser = configparser.ConfigParser()
            try:
                Parser.read(self.file)
            except Exception as e:
                self.app.Logging.output("Error parsing configuration file from "+self.file+", error: "+str(e), "critical", True)
                sys.exit(os.EX_CONFIG)

            # all configuration sections
            Sections = Parser.sections()

            for Section in Sections:
                Options = Parser.options(Section)
                self.Config[Section] = dict()

                # and configuration variables inside of sections
                for Option in Options:
                    self.Config[Section][Option] = Parser.get(Section, Option)

        self.configTime = os.path.getmtime(self.file)

#c = Config("asd", "/home/webnull/.nbnotify/config")
#c.loadConfig()
#print c.getKey("global", "checktime")
