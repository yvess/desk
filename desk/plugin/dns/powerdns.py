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
        self.domain = None
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
        self._cursor.execute(sql)
        self._conn.commit()
        return self._cursor

    def check_domain(self, domain):
        lookup_domain = self._db('SELECT id FROM domains WHERE name="{}"'.format(domain)).fetchone()
        has_domain = True if lookup_domain else False
        return has_domain

    def set_domain(self, domain, new=False):
        self.domain = domain
        if not new:
            self.domain_id = self._db('SELECT id FROM domains WHERE name="{}"'.format(domain)).fetchone()[0]
            print(self.domain_id)
            #if self.domain_id:
            #    self.domain_id = self.domain_id[0]

    def add_domain(self, domain=None):
        if domain:
            self.set_domain(domain, new=True)
        self._db("INSERT INTO domains (name, type) VALUES ('{}', 'NATIVE')".format(self.domain))
        self.domain_id = self._cursor.lastrowid
        self.add_record(self.domain, 'localhost dnsmaster@test.tt 1', rtype="SOA")  # TODO: where to put SOA?

    def del_domain(self, domain=None):
        if domain:
            self.set_domain(domain)
        self._db("DELETE FROM records WHERE domain_id={}".format(self.domain_id))
        self._db("DELETE FROM domains WHERE id={}".format(self.domain_id))

    def add_record(self, key, value, rtype='A', ttl=86400, priority='NULL', domain=None):
        if domain:
            self.set_domain(domain)
        # TOOD set ttl
        self._db(
            """INSERT INTO records
               (domain_id, name, content, type, ttl, prio)
               VALUES
               ({domain_id},'{key}','{value}','{rtype}',{ttl},{priority})
            """.format(
                domain_id=self.domain_id, key=key, value=value, rtype=rtype, ttl=ttl, priority=priority
            )
        )

    def update_record(self, key, value, rtype='A', ttl=86400, priority='NULL', domain=None):
        if domain:
            self.set_domain(domain)
        # TOOD set ttl
        self._db(
            """UPDATE records
               SET domain_id={domain_id}, name='{key}', content='{value}',
                   type='{rtype}',ttl={ttl},prio={priority}
               WHERE name='{key}' AND type='{rtype}'
            """.format(
                domain_id=self.domain_id, key=key, value=value, rtype=rtype, ttl=ttl, priority=priority
            )
        )

    def del_record():
        pass

    def create(self):
        sucess = False
        if self.doc:
            self.set_domain(self.doc['domain'], new=True)
            self.add_domain()
            for nameserver in [n.strip() for n in self.doc['nameservers'].split(",")]:
                self.add_record(self.domain, nameserver, rtype="NS")
            if 'a' in self.doc:
                for a in self.doc['a']:
                    self.add_record(".".join([a['host'], self.domain]), a['ip'], rtype="A")  # TODO add special case for main @ self.domain?
            if 'cname' in self.doc:
                for cname in self.doc['cname']:
                    self.add_record(".".join([cname['alias'], self.domain]), cname['host'], rtype="CNAME")
            if 'mx' in self.doc:
                for mx in self.doc['mx']:
                    self.add_record(self.domain, mx['host'], priority=int(mx['priority']), rtype="MX")
            self._conn.commit()
        return sucess

    def update(self):
        sucess = False
        if self.doc:
            self.set_domain(self.doc['domain'])
        if self.diff:
            # TODO nameserver record
            rtypes = [
                {
                    'name': 'a',
                    'key_trans': lambda k: ".".join([k, self.domain]),
                    'map': {'key': 'host', 'value': 'ip'}
                }
                #'cname': {'key_trans': lambda k: ".".join([k, self.domain])},
                #'mx': {'key_trans': lambda k: ".".join([k, self.domain])}
            ]  # ".".join([a['host'], domain])
            for rtype in rtypes:
                # for key, value in self.diff['_append'][rtype]:
                #     if 'key_trans' in rtypes[rtype]:
                #         key = rtypes['key_trans'](key)
                #     self.add_record(key, value, rtype=rtype.upper())  # TODO add special case for main @ domain?
                #print("RTYPE", rtype, self.diff['_update'][rtype])
                update = self.diff['update'][rtype['name']]
                for d in update:
                    key, value = d[rtype['map']['key']], d[rtype['map']['value']]
                    if 'key_trans' in rtype:
                        key = rtype['key_trans'](key)
                    self.update_record(key, value, rtype=rtype['name'].upper())
                # for key, value in self.diff['_remove'][rtype]:
                #     self.del_record(key, value, rtype=rtype.upper())
            self._conn.commit()
        return sucess
