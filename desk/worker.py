#!/usr/bin/env python
# coding: utf-8
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function

import sys
import os
from ConfigParser import SafeConfigParser
from ConfigParser import ParsingError
import argparse
sys.path.append("../")
from desk import Worker
from deks.utls import put_json


def setup_parser():
    """create the command line parser / config file reader """

    defaults = {
        "couchdb_uri": "http://localhost:5984",
        "couchdb_db": "desk_drawer",
    }
    # first only parse the config file argument
    conf_parser = argparse.ArgumentParser(add_help=False)
    conf_parser.add_argument("-c", "--config", dest="config",
        default="/etc/desk/worker.conf",
        help="path to the config file, default: /etc/desk/worker.conf",
        metavar="FILE"
    )
    args, remaining_args = conf_parser.parse_known_args()
    # load config files with settings, puts them into a dict format "section_option"
    if args.config:
        config = SafeConfigParser()
        if not config.read([args.config]):
            print("Can't open file '{}'".format(args.config))
            sys.exit(0)
        else:
            for section in ['couchdb']:  # put in here all your sections
                defaults.update(
                    {'{}_{}'.format(section, k):v for k, v in config.viewitems(section)}
                )
    # parse all other arguments
    parser = argparse.ArgumentParser(
        parents=[conf_parser],
        description="""Worker is the agent for the desk plattform.
                       Command line switches overwrite config file settings""",
    )
    parser.set_defaults(**defaults)
    parser.add_argument("-u", "--couchdb_uri", dest="couchdb_uri",
        metavar="URI", help="connection url of the server")
    parser.add_argument("-d", "--couchdb_db", dest="couchdb_db",
        metavar="NAME", help="database of the server")

    args = parser.parse_args(remaining_args)

    return args

if __name__ == "__main__":
    settings = setup_parser()
    worker = Worker(settings)
    worker.run()
