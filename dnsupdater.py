#!/usr/bin/python

import ConfigParser
import os.path

import dns.query
import dns.tsigkeyring
import dns.update

import ipaddr

import logging
import logging.handlers

# Overrule call to dns.Name.to_wire:
# There's an issue with compression in the tsig section, which we can't really
# disable.  The best we can do is to overrule the Name.to_wire() method so it
# never compresses, then things do work.
orig_to_wire = dns.name.Name.__dict__["to_wire"]
def new_to_wire(self, output, compress, origin):
    return orig_to_wire(self, output, None, origin)
dns.name.Name.to_wire = new_to_wire

class Name:
    def __init__(self, name, parser):
        self._name = name
        self._zone = parser.get(name, 'zone')
        self._key = parser.get(name, 'key')
        self._server = parser.get(name, 'server')
        self._updateIPv4 = parser.getboolean(name, 'update-v4')
        self._updateIPv6 = parser.getboolean(name, 'update-v6')

        if not self._name.endswith("."):
            logging.debug("Append '.' to %s" % self._name)
            self._name = "%s." % self._name

    def name(self):
        return self._name

    def key(self):
        return self._key

    def zone(self):
        return self._zone

    def server(self):
        return self._server

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
            logging.info("Reading config file %s" % self.config_file())
            parser.read(self.config_file())
        except ConfigParser.ParsingError, err:
            print "Failed to load config %s: %s" % (self.config_file(), err)

        self._names = []
        for name in parser.sections():
            n = Name(name, parser)
            logging.debug("Found name %s" % n)
            self._names.append(n)

    def get_names(self):
        return self._names

class DNSUpdater:
    def __init__(self, conf):
        self._conf = conf
        self._cached_v4 = {}
        self._cached_v6 = {}

    def update_addresses_for_name(self, name, v4, v6):
        keyring = dns.tsigkeyring.from_text({ name.name(): name.key() })
        zone = dns.name.from_text(name.name())
        update = dns.update.Update(name.zone(),
                    keyring=keyring,
                    keyname=name.name(),
                    keyalgorithm=dns.tsig.HMAC_SHA256)

        if name.updateIPv4():
            update.delete(name.name(), 'A')
            for addr in v4:
                logging.debug("Add A record for %s" % addr)
                update.add(name.name(), 60, 'A', addr)
        if name.updateIPv6():
            update.delete(name.name(), 'AAAA')
            for addr in v6:
                logging.debug("Add AAAA record for %s" % addr)
                update.add(name.name(), 60, 'AAAA', addr)

        logging.info("Update DNS entries for %s on server %s" % (name.name(), name.server()))
        try:
            response = dns.query.udp(update, name.server())
        except Exception, e:
            logging.warn("DNS update failed: %s (%s)" % (e, type(e)))
            # Clear cache so we try again next time.
            self._cached_v4 = []
            self._cached_v6 = []

    def is_publishable(self, v6addr):
        a = ipaddr.IPv6Address(v6addr)
        if a.is_link_local:
            return False
        if a.is_private:
            return False
        if a.is_site_local:
            return False
        return True

    def filter_v6(self, v6):
        return filter(lambda addr: self.is_publishable(addr), v6)

    def have_addresses_changed(self, v4, v6):
        if v4 != self._cached_v4:
            return True
        if v6 != self._cached_v6:
            return True
        return False

    def update_addresses(self, v4, v6):
        v6 = self.filter_v6(v6)

        if not self.have_addresses_changed(v4, v6):
            return

        self._cached_v4 = v4
        self._cached_v6 = v6

        names = self._conf.get_names()
        for name in names:
            self.update_addresses_for_name(name, v4, v6)

def setup_logger():
        lvl = logging.DEBUG
        fmt = "dnsupdater: %(asctime)s:%(levelname)s:%(module)s:%(message)s"
        logging.basicConfig(level=lvl, format=fmt)

        # Default output to syslog
        syslog = logging.handlers.SysLogHandler()
        syslog_formatter = logging.Formatter('dnsupdater:%(message)s')
        syslog.setFormatter(syslog_formatter)
        logger = logging.getLogger()
        logger.addHandler(syslog)

def main():
    setup_logger()

    import addrmon
    conf = ConfigLoader()
    updater = DNSUpdater(conf)
    mon = addrmon.AddrMon(updater.update_addresses)
    mon.start()

if __name__ == "__main__":
    main()
