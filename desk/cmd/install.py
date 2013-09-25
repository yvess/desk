# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals, division  # python3
from couchdbkit.loaders import FileSystemDocsLoader
from couchdbkit import Server
from . import SettingsCommand


class InstallCommand(SettingsCommand):
    def __init__(self, *args, **kwargs):
        super(InstallCommand, self).__init__(*args, **kwargs)

    def upload_design_doc(self):
        server = Server(self.settings.couchdb_uri)
        db = server.get_or_create_db("desk_drawer")
        loader = FileSystemDocsLoader('./_design')
        loader.sync(db, verbose=True)
