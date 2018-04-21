import Foundation
import SystemConfiguration

class AddrMon:
    def __init__(self, update_callback):
        self._update_callback = update_callback

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

    def _callback(self, store, keys, info):
        # We'll be lazy and just re-query all information and update in one go.
        self.update()

    def start(self):
        logging.debug("Starting address monitoring loop")
        self.update()
        SystemConfiguration.CFRunLoopRun()

    def get_primary_interface(self):
        # Assume that it's the same interface for IPv4 and IPv6
        val = SystemConfiguration.SCDynamicStoreCopyValue(self._store, "State:/Network/Global/IPv4")
        if not val:
            logging.warn("No response to Sate:/Network/Global/IPv4")
            return None
        return Foundation.CFDictionaryGetValue(val, "PrimaryInterface")

    def get_addrs(self, primary_if, proto):
        val = SystemConfiguration.SCDynamicStoreCopyValue(self._store, "State:/Network/Interface/%s/%s" % (primary_if, proto))
        if not val:
            logging.warn("No %s on %s" % (primary_if, proto))
            return []
        if not Foundation.CFDictionaryGetValue(val, "Addresses"):
            logging.warn("No %s Addresses field" % proto)
            return []

        addrs = Foundation.CFDictionaryGetValue(val, "Addresses")

        result = []
        for i in range(Foundation.CFArrayGetCount(addrs)):
            result.append(str(Foundation.CFArrayGetValueAtIndex(addrs, i)))

        return result

    def update(self):
        primary_if = self.get_primary_interface()
        if not primary_if:
            return
        v4 = self.get_addrs(primary_if, "IPv4")
        v6 = self.get_addrs(primary_if, "IPv6")

        if not v4 and not v6:
            return

        logging.info("Found addresses %s, %s" % (v4, v6))
        self._update_callback(v4, v6)


