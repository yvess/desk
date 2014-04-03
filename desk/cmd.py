# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals, division  # python3

import os
import logging
from couchdbkit.loaders import FileSystemDocsLoader
from couchdbkit import Server
from desk.utils import ObjectDict
from desk import Worker, Foreman
from desk.utils import CouchdbUploader


class SettingsCommand(object):
    def set_settings(self, settings, hostname=os.uname()[1]):
        if isinstance(settings, dict):
            settings = ObjectDict(**settings)
        self.hostname = hostname
        self.settings = settings
        if hasattr(settings, 'loglevel') and settings.loglevel:
            loglevel = getattr(logging, settings.loglevel.upper(), 30)
            logger = logging.getLogger()
            logger.setLevel(loglevel)


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


class DocsProcessor(SettingsCommand):
    def __init__(self, settings, docs):
        self.set_settings(settings)
        template_ids, map_id = (self.settings.template_ids.split(','),
                                self.settings.map_id)
        self.server = Server(uri=self.settings.couchdb_uri)
        self.db = self.server.get_db(self.settings.couchdb_db)
        self.template_docs = (self.get_templates(template_ids)
                              if template_ids else None)
        self.map_doc = self.get_map(map_id) if map_id else None
        self.docs = docs

    def get_templates(self, template_ids):
        docs = []
        for doc_id in template_ids:
            template_doc = self.db.get(doc_id)
            for attr in ['_id', '_rev', 'type', 'template_type', 'name']:
                del template_doc[attr]
            has_postprocess_tpl = hasattr(self, 'postprocess_tpl')
            if has_postprocess_tpl and callable(self.postprocess_tpl):
                template_doc = self.postprocess_tpl(template_doc)
            docs.append(template_doc)
        return docs

    def get_map(self, map_id):
        return self.db.get(map_id)

    def is_child_of(self, parent, child):
        def is_child_of_inner(parent, child):
            for key, value in child.iteritems():
                if key in parent and parent[key] == value:
                    yield True
                else:
                    yield False
        return all(is_child_of_inner(parent, child))

    def replace_with_template(self, doc, template):
        for key in template.keys():
            del doc['key']
        doc.update(template)

    def process_doc(self, doc):
        for template in self.template_docs:
            if self.is_child_of(doc, template):
                self.replace_with_template(doc, template)
                break

    def process(self):
        for doc in self.docs:
            self.process_doc(doc)
