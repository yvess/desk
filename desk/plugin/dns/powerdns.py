# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
import sqlite3
import time
import os
from copy import copy
from desk.plugin.dns import DnsBase


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

    def update_serial(self, domain=None):
        if domain:
            self.set_domain(domain)
        current_serial = self._db(
            'SELECT content FROM records WHERE name="{}" AND type="SOA"'.format(self.domain)
        ).fetchone()[0].split(" ")[-1]
        serial_datetime, serial_counter = current_serial[:-4], int(current_serial[-4:])
        current_datetime = time.strftime("%Y%m%d%H%M", time.localtime())
        if serial_datetime == current_datetime:
            serial_counter += 1
        serial = "{}{:04d}".format(current_datetime, serial_counter)
        self.update_record(self.domain, "localhost dnsmaster@test.tt {}".format(serial), rtype="SOA")
        os.system("sudo pdns_control purge {}$".format(self.domain))  # TODO sudoers

    def add_domain(self, domain=None):
        if domain:
            self.set_domain(domain, new=True)
        self._db("INSERT INTO domains (name, type) VALUES ('{}', 'NATIVE')".format(self.domain))
        self.domain_id = self._cursor.lastrowid
        serial = time.strftime("%Y%m%d%H%M0001", time.localtime())
        self.add_record(self.domain, "localhost dnsmaster@test.tt {}".format(serial), rtype="SOA")  # TODO: where to put SOA?

    def del_domain(self, domain=None):
        if domain:
            self.set_domain(domain)
        self._db("DELETE FROM records WHERE domain_id={}".format(self.domain_id))
        self._db("DELETE FROM domains WHERE id={}".format(self.domain_id))

    def add_record(self, key, value, rtype='A', ttl=86400, priority='NULL', domain=None):
        if domain:
            self.set_domain(domain)
        # TOOD set ttl
        if value.startswith('@ip_'):  # get ip value from hashmap
            value = self.lookup_map[value]
        self._db(
            """INSERT INTO records
               (domain_id, name, content, type, ttl, prio)
               VALUES
               ({domain_id},'{key}','{value}','{rtype}',{ttl},{priority})
            """.format(
                domain_id=self.domain_id, key=key, value=value, rtype=rtype, ttl=ttl, priority=priority
            )
        )

    def update_record(self, key, value, rtype='A', ttl=86400, priority='NULL', domain=None, lookup='key'):
        if domain:
            self.set_domain(domain)
        # TOOD set ttl
        if value.startswith('@ip_'):  # get ip value from hashmap
            value = self.lookup_map[value]
        if lookup == 'key':
            where = "name='{}'".format(key)
        elif lookup == 'value':
            where = "content='{}'".format(value)
        self._db(
            """UPDATE records
               SET domain_id={domain_id}, name='{key}', content='{value}',
                   ttl={ttl},prio={priority}
               WHERE {lookup} AND type='{rtype}'
            """.format(
                domain_id=self.domain_id, key=key, value=value, rtype=rtype, ttl=ttl, priority=priority, lookup=where
            )
        )

    def del_record(self, key, value, rtype='A', domain=None):
        if domain:
            self.set_domain(domain)
        self._db(
            """DELETE FROM records
               WHERE name='{key}' AND type='{rtype}'
            """.format(
                domain_id=self.domain_id, key=key, value=value, rtype=rtype
            )
        )

    def create(self):
        sucess = False
        if self.doc:
            self.set_domain(self.doc['domain'], new=True)
            self.add_domain()
            for nameserver in [n.strip() for n in self.doc['nameservers'].split(",")]:
                self.add_record(self.domain, nameserver, rtype="NS")
            for rtype in self.structure:
                name, key_id, value_id = rtype['name'], rtype['key_id'], rtype['value_id']
                if name in self.doc:
                    for d in self.doc[name]:  # TODO merge with create logic
                        key = rtype['key_trans'](d[key_id], self.domain) if 'key_trans' in rtype else d[key_id]
                        value = rtype['value_trans'](d[value_id], self.domain) if 'value_trans' in rtype else d[value_id]
                        if name.upper() == "MX":
                            self.add_record(self.domain, key, priority=int(value), rtype="MX")
                        else:
                            self.add_record(key, value, rtype=name.upper())  # TODO add special case for main @ self.domain?
            self._conn.commit()
            self.update_serial()
        return sucess

    def _trans(self, key, value, rtype=None):
        key = rtype['key_trans'](key, self.domain) if 'key_trans' in rtype else key
        value = rtype['value_trans'](value, self.domain) if 'value_trans' in rtype else value
        return (key, value)

    def update(self):
        sucess = False
        if self.doc:
            self.set_domain(self.doc['domain'])
        if self.diff:
            # TODO nameserver record
            for rtype in self.structure:
                name, key_id, value_id = rtype['name'], rtype['key_id'], rtype['value_id']
                # remove records
                remove = self.diff['remove'][name] if name in self.diff['remove'] else []
                for d in remove:
                    key, value = self._trans(d[key_id], d[value_id], rtype=rtype)
                    self.del_record(key, value, rtype=name.upper())
                # new records
                append = self.diff['append'][name] if name in self.diff['append'] else []
                for d in append:
                    key, value = self._trans(d[key_id], d[value_id], rtype=rtype)
                    self.add_record(key, value, rtype=name.upper())
                # update records
                update = self.diff['update'][name] if name in self.diff['update'] else []
                for d in update:
                    key, value = self._trans(d[key_id], d[value_id], rtype=rtype)
                    lookup = d['lookup']
                    if lookup in ('key', 'value'):
                        self.update_record(key, value, rtype=name.upper(), lookup=lookup)
                    elif lookup == 'id':
                        record = copy(d)
                        del record['lookup']
                        index = self.doc[name].index(record)
                        d_old = self.prev_doc[name][index]
                        key_old, value_old = self._trans(d_old[key_id], d_old[value_id], rtype=rtype)
                        self.del_record(key_old, value_old, rtype=name.upper())
                        self.add_record(key, value, rtype=name.upper())
            self._conn.commit()
            self.update_serial()
        return sucess
