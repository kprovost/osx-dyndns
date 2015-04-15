#!/usr/bin/python

import ConfigParser
import os.path

import Foundation
import SystemConfiguration

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

class AddrMon:
    def __init__(self, conf):
        self._conf = conf

        self._store = SystemConfiguration.SCDynamicStoreCreate(None,
                             "global-network-watcher",
                             self._callback,
                             None)

        SystemConfiguration.SCDynamicStoreSetNotificationKeys(self._store,
                                          None,
                                          [
                                              'State:/Network/Global/IPv4',
                                              'State:/Network/Global/IPv6',
                                              'State:/Network/Interface/.*/IPv4',
                                              'State:/Network/Interface/.*/IPv6'
                                          ])
        Foundation.CFRunLoopAddSource(Foundation.CFRunLoopGetCurrent(),
                           SystemConfiguration.SCDynamicStoreCreateRunLoopSource(None, self._store, 0),
                           Foundation.kCFRunLoopCommonModes)

    def _callback(self):
        print "Callback!"

    def start(self):
        self.initial_update()
        SystemConfiguration.CFRunLoopRun()

    def get_primary_interface(self):
        # Assume that it's the same interface for IPv4 and IPv6
        val = SystemConfiguration.SCDynamicStoreCopyValue(self._store, "State:/Network/Global/IPv4")
        return Foundation.CFDictionaryGetValue(val, "PrimaryInterface")

    def get_addrs(self, primary_if, proto):
        val = SystemConfiguration.SCDynamicStoreCopyValue(self._store, "State:/Network/Interface/%s/%s" % (primary_if, proto))
        if not val or not Foundation.CFDictionaryGetValue(val, "Addresses"):
            raise Exception("No %s Addresses field" % proto)

        addrs = Foundation.CFDictionaryGetValue(val, "Addresses")

        result = []
        for i in range(Foundation.CFArrayGetCount(addrs)):
            result.append(Foundation.CFArrayGetValueAtIndex(addrs, i))

        return result

    def initial_update(self):
        primary_if = self.get_primary_interface()
        v4 = self.get_addrs(primary_if, "IPv4")
        v6 = self.get_addrs(primary_if, "IPv6")


def main():
    conf = ConfigLoader()
    mon = AddrMon(conf)

main()
