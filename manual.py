#!/usr/bin/env python

import dnsupdater
import sys

def main():
    dnsupdater.setup_logger()

    conf = dnsupdater.ConfigLoader()
    updater = dnsupdater.DNSUpdater(conf)
   
    updater.update_addresses([sys.argv[1]], [])

if __name__ == "__main__":
    main()
