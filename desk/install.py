#!/usr/bin/env python
# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals, division  # python3
import argparse
from couchdbkit.loaders import FileSystemDocsLoader
from couchdbkit import Server


def setup_parser():
    """install the couchdb design docs"""
    parser = argparse.ArgumentParser(
        description="install helper for first install of desk"
    )
    parser.add_argument(
        "host", nargs="?",
        default="localhost", help="couchdb user"
    )
    parser.add_argument(
        "-u", "--user", dest="user",
        default="", help="couchdb user"
    )
    parser.add_argument(
        "-p", "--passwd", dest="passwd",
        default="", help="couchdb password"
    )
    args = parser.parse_args()

    return (args, parser)


def upload_design_doc(user=None, passwd=None, host="localhost"):
    if user:
        uri = "http://{}:{}@{}:5984".format(user, passwd, host)
    else:
        uri = "http://{}:5984".format(host)
    server = Server(uri=uri)
    db = server.get_or_create_db("desk_drawer")
    loader = FileSystemDocsLoader('./_design')
    loader.sync(db, verbose=True)


def main():
    args, parser = setup_parser()
    upload_design_doc(user=args.user, passwd=args.passwd, host=args.host)

if __name__ == "__main__":
    main()
