#!/usr/bin/python

import ConfigParser
import os.path

class Name:
    def __init__(self, name, parser):
        self._name = name
        self._key = parser.get(name, 'key')
        self._updateIPv4 = parser.getboolean(name, 'update-v4')
        self._updateIPv6 = parser.getboolean(name, 'update-v6')

    def name(self):
        return self._name

    def key(self):
        return self._key

    def updateIPv4(self):
        return self._updateIPv4

    def updateIPv6(self):
        return self._updateIPv6

    def __repr__(self):
        return "%s (Update V4: %s, Update V6 %s)" % (self._name, self._updateIPv4, self._updateIPv6)

class ConfigLoader:
    def config_file(self):
        home = os.path.expanduser("~")
        return "%s/.dnsupdater.ini" % home

    def __init__(self):
        try:
            parser = ConfigParser.SafeConfigParser()
            parser.read(self.config_file())
        except ConfigParser.ParsingError, err:
            print "Failed to load config %s: %s" % (self.config_file(), err)

        self._names = []
        for name in parser.sections():
            self._names.append(Name(name, parser))

def main():
    c = ConfigLoader()

main()
