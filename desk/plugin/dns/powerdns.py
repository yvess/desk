# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from desk.plugin.dns import DnsBase
import sqlite3


class Powerdns(DnsBase):
    SETTING_KEYS = ['backend', 'db', 'user', 'name']

    def __init__(self, settings):
        self.settings = settings
        self.doc = None
        self.domain_id = None
        if hasattr(settings, 'powerdns_backend') and settings.powerdns_backend == 'sqlite':
            self._conn = sqlite3.connect(settings.powerdns_db)
            self._cursor = self._conn.cursor()
        else:
            raise Exception("can't init database")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._conn.close()

    def _db(self, sql):
        try:
            self._cursor.execute(sql)
            self._conn.commit()
            return self._cursor
        except sqlite3.IntegrityError:
            raise Exception("db database problem")

    def add_domain(self, domain):
        self._db("INSERT INTO domains (name, type) VALUES ('{}', 'NATIVE')".format(domain))
        self.domain_id = self._cursor.lastrowid
        self.add_record(domain, 'localhost y@yas.ch 1', rtype="SOA")  # TODO: where to put SOA?

    def del_domain(self, domain):
        domain_id = self._db("SELECT id FROM domains WHERE name='{}'".format(domain)).fetchone()[0]
        self._db("DELETE FROM records WHERE domain_id={}".format(domain_id))
        self._db("DELETE FROM domains WHERE id={}".format(domain_id))

    def add_record(self, key, value, rtype='A', ttl=86400, priority='NULL'):
        if self.domain_id:
            self._db(
                """INSERT INTO records (domain_id, name, content, type, ttl, prio)
                   VALUES ({domain_id},'{key}','{value}','{rtype}',{ttl},{priority})""".format(
                    domain_id=self.domain_id, key=key, value=value, rtype=rtype, ttl=ttl, priority=priority
                )
            )
        else:
            pass  # TODO else?

    def update_record(self, key, value, rtype='A', ttl=86400, priority='NULL'):
        if self.domain_id:
            pass

    def del_record():
        pass

    def create(self):
        sucess = False
        domain = self.doc['domain']  # TODO put in init
        if self.doc:
            self.add_domain(domain)
            for nameserver in [n.strip() for n in self.doc['nameservers'].split(",")]:
                self.add_record(domain, nameserver, rtype="NS")
            if 'a' in self.doc:
                for a in self.doc['a']:
                    self.add_record(".".join([a['host'], domain]), a['ip'], rtype="A")  # TODO add special case for main @ domain?
            if 'cname' in self.doc:
                for cname in self.doc['cname']:
                    self.add_record(".".join([cname['alias'], domain]), cname['host'], rtype="CNAME")
            if 'mx' in self.doc:
                for mx in self.doc['mx']:
                    self.add_record(domain, mx['host'], priority=int(mx['priority']), rtype="MX")
            self._conn.commit()
        return sucess

    def update(self):
        sucess = False
        domain = self.doc['domain']  # TODO put in init
        if self.diff:
            # TODO nameserver record
            rtypes = {
                'a': {'ktrans': lambda k: ".".join([k, domain])},
                'cname': None,
                'mx': None
            }  # ".".join([a['host'], domain])
            for rtype in rtypes.viewkeys():
                for key, value in self.diff['_append'][rtype]:
                    if 'ktrans' in rtypes[rtype]:
                        key = rtypes['ktrans'](key)
                    self.add_record(key, value, rtype=rtype.upper())  # TODO add special case for main @ domain?
                for key, value in self.diff['_update'][rtype]:
                    self.update_record(key, value, rtype=rtype.upper())
                for key, value in self.diff['_remove'][rtype]:
                    self.del_record(key, value, rtype=rtype.upper())
            self._conn.commit()
        return sucess
