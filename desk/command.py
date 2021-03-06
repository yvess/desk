# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals, division  # python3

import os
import socket
import logging
import time
from couchdbkit.loaders import FileSystemDocsLoader
from couchdbkit import Server
from couchdbkit.resource import ResourceNotFound
from desk.utils import ObjectDict
from desk import Worker, Foreman
from desk.utils import CouchdbUploader
from desk import migrations


class SettingsCommand(object):
    def set_settings(self, settings, hostname=socket.getfqdn()):
        if isinstance(settings, dict):
            settings = ObjectDict(**settings)
        self.hostname = hostname
        self.settings = settings
        if hasattr(settings, 'loglevel') and settings.loglevel:
            loglevel = getattr(logging, settings.loglevel.upper(), 30)
            logger = logging.getLogger()
            logger.setLevel(loglevel)


class SettingsCommandDb(SettingsCommand):
    def set_settings(self, settings, hostname=socket.getfqdn()):
        super(SettingsCommandDb, self).set_settings(settings, hostname)
        self.server = Server(uri=self.settings.couchdb_uri)
        self.db = self.server.get_db(self.settings.couchdb_db)

    def _cmd(self, cmd):
        return "{}/{}".format(self.settings.couchdb_db, cmd)


class WorkerCommand(SettingsCommand):
    def set_settings(self, settings, *args, **kwargs):
        super(WorkerCommand, self).set_settings(settings, *args, **kwargs)
        if self.settings.worker_is_foreman:
            self.worker = Foreman(self.settings)
        else:
            self.worker = Worker(self.settings)

    def setup_parser(self, subparsers, config, verbose):
        worker_parser = subparsers.add_parser(
            'run',
            help="""run the worker and/or foreman agent""",
            description="Command line switches overwrite config file settings."
        )
        worker_parser.add_argument(*config['args'], **config['kwargs'])
        worker_parser.add_argument(*verbose['args'], **verbose['kwargs'])
        worker_parser.add_argument(
            "-o", "--run_once", dest="worker_daemon",
            help="run only once not as daemon",
            action="store_false", default=True
        )
        worker_parser.add_argument(
            "-u", "--couchdb_uri", dest="couchdb_uri",
            metavar="URI", help="connection url of the server"
        )
        worker_parser.add_argument(
            "-d", "--couchdb_db", dest="couchdb_db",
            metavar="NAME", help="database of the server"
        )
        worker_parser.add_argument(
            "-f", "--foreman", dest="worker_is_foreman",
            help="be the foreman and a worker", action="store_true"
        )
        return worker_parser

    def run(self):
        if self.settings.worker_daemon:
            self.worker.run()
        else:
            self.worker.run_once()


class InstallDbCommand(SettingsCommand):
    def setup_parser(self, subparsers, config_parser):
        install_parser = subparsers.add_parser(
            'install-db',
            help="""install the couchdb design docs""",
        )
        install_parser.add_argument(
            *config_parser['args'], **config_parser['kwargs']
        )

        return install_parser

    def run(self):
        server = Server(self.settings.couchdb_uri)
        db = server.get_or_create_db(self.settings.couchdb_db)
        loader = FileSystemDocsLoader('./_design')
        loader.sync(db, verbose=True)


class UploadJsonCommand(SettingsCommand):
    def setup_parser(self, subparsers, config_parser):
        upload_parser = subparsers.add_parser(
            'upload-json',
            help="""upload multiple docs to couchdb""",
        )
        upload_parser.add_argument(
            *config_parser['args'], **config_parser['kwargs']
        )
        upload_parser.add_argument(
            "path", help="path of dir with json files",
        )

        return upload_parser

    def run(self):
        couch_up = CouchdbUploader(
            path=self.settings.path, couchdb_uri=self.settings.couchdb_uri,
            couchdb_db=self.settings.couchdb_db
        )

        for fname in os.listdir(self.settings.path):
            couch_up.put(
                data="@{}".format(fname),
                doc_id=fname[:-5]
            )


class InstallWorkerCommand(SettingsCommand):
    def setup_parser(self, subparsers, config_parser):
        install_parser = subparsers.add_parser(
            'install-worker',
            help="""install worker settings into the couchdb database""",
        )
        install_parser.add_argument(
            *config_parser['args'], **config_parser['kwargs']
        )

        return install_parser

    def run(self):
        server = Server(self.settings.couchdb_uri)
        db = server.get_db(self.settings.couchdb_db)
        provides = {}
        if hasattr(self.settings, 'worker_dns'):
            provides['domain'], worker_dns = [], self.settings.worker_dns
            dns_servers = map(
                lambda x: x.strip().split(':'), worker_dns.split(',')
            )
            for backend, name in dns_servers:
                provides['domain'].append({'backend': backend, 'name': name})

        worker_id = "worker-{}".format(self.hostname)
        d = {
            "_id": worker_id, "type": "worker", "hostname": self.hostname,
            "provides": provides
        }
        db.save_doc(d)


class MigrateCommand(SettingsCommand):
    def setup_parser(self, subparsers, config_parser):
        migrate_parser = subparsers.add_parser(
            'migrate',
            help="""upgrade all documents to the latest verision""",
        )
        migrate_parser.add_argument(
            *config_parser['args'], **config_parser['kwargs']
        )

        return migrate_parser

    def _cmd(self, cmd):
        return "{}/{}".format(self.settings.couchdb_db, cmd)

    def run(self):
        server = Server(self.settings.couchdb_uri)
        db = server.get_db(self.settings.couchdb_db)

        def next_migration(version, doc_id, doc_type):
            new_version = version + 1
            next_migration_name = "to%04d" % new_version
            if hasattr(migrations, next_migration_name):
                do_migration = getattr(migrations, next_migration_name)
                doc = db.get(doc_id)
                print('updating to:', new_version, doc_type, doc_id)
                do_migration(doc, doc_type, db)
                next_migration(new_version, doc_id, doc_type)

        for item in db.view(self._cmd("version")):
            version, doc_id, doc_type = item['key'], item['id'], item['value']
            next_migration(version, doc_id, doc_type)


class DocsProcessor(SettingsCommand):
    allowed_template_type = None  # needs to be set by subclass
    map_id = None  # needs to be set by subclass
    replace_id = None  # needs to be set by subclass
    _map_cache = None
    _map_cache_time = None

    @classmethod
    def map_cache(cls):
        if cls._map_cache_time and time.time() > (cls._map_cache_time + 3600):
            cls._map_cache = None
        return cls._map_cache

    @classmethod
    def set_map_cache(cls, value):
        cls._map_cache_time = time.time()
        cls._map_cache = value

    def __init__(self, settings, docs):
        self.set_settings(settings)
        template_ids, map_id = self.settings.template_ids, self.settings.map_id
        template_ids = template_ids.split(',') if template_ids else []
        self.server = Server(uri=self.settings.couchdb_uri)
        self.db = self.server.get_db(self.settings.couchdb_db)
        self.template_docs, self.map_keys = [], None
        if not template_ids:
            self.template_docs = self.get_all_templates()
        else:
            self.template_docs = self.get_templates(template_ids)
        if self.map_id:
            self.map_dict = self.get_map()
            self.map_keys = self.map_dict.keys()
        if self.replace_id:
            self.replace_dict = self.get_replace()
            self.replace_keys = self.replace_dict.keys()
        self.docs = docs

    def clean_template(self, template_doc):
        attrs_to_delete = [
            '_rev', 'type', 'template_type', 'template_autoload', 'name'
        ]
        for attr in attrs_to_delete:
            del template_doc[attr]
        if (hasattr(self, 'postprocess_tpl')
           and callable(self.postprocess_tpl)):
            template_doc = self.postprocess_tpl(template_doc)
        return template_doc

    def get_map(self):
        map_dict = self.map_cache()
        if map_dict:
            return map_dict
        try:
            map_dict = self.db.get(self.map_id)['map']
            self.set_map_cache(map_dict)
        except ResourceNotFound:
            pass
        return map_dict

    def get_replace(self):
        replace_dict = None
        try:
            replace_dict = self.db.get(self.replace_id)['replace']
        except ResourceNotFound:
            pass
        return replace_dict

    def get_templates(self, template_ids):
        docs = []
        for doc_id in template_ids:
            template_doc = self.clean_template(self.db.get(doc_id))
            docs.append(template_doc)
        return docs

    def get_all_templates(self):
        docs = []
        for t in self.db.view("%s/template" % (self.settings.couchdb_db)):
            template_doc = self.db.get(t['id'])
            if (template_doc['template_type'] == self.allowed_template_type
               and 'template_autoload' in template_doc
               and template_doc['template_autoload'] is True):
                docs.append(self.clean_template(template_doc))
        # assumption that templates with more keys will be checked first
        docs.sort(key=len)
        docs.reverse()
        return docs

    def is_child_of(self, parent, child):
        def is_child_of_inner(parent, child):
            for key, value in child.iteritems():
                if key in parent and (parent[key] == value or key == '_id'):
                    yield True
                else:
                    yield False
        is_child = all(is_child_of_inner(parent, child))
        return is_child

    def replace_with_template(self, doc, template):
        for key in template.keys():
            if key != '_id':
                del doc[key]
        doc['template_id'] = template['_id']

    def process_doc(self, doc):
        if self.template_docs:
            for template in self.template_docs:
                if self.is_child_of(doc, template):
                    self.replace_with_template(doc, template)
                    break
        if (hasattr(self, 'postprocess_doc')
           and callable(self.postprocess_doc)):
            doc = self.postprocess_doc(doc)
        return doc

    def process(self):
        for doc in self.docs:
            doc[1] = self.process_doc(doc[1])
