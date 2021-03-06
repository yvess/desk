# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
import sqlite3
import time
import os
import logging
from copy import copy
from collections import OrderedDict
import traceback
from desk.plugin.dns import DnsBase, reverse_fqdn

SOA_FORMAT = "{soa_primary} {soa_hostmaster} {serial} {soa_refresh} {soa_retry} {soa_expire} {soa_default_ttl}"
logging.basicConfig(level=logging.INFO)


class Powerdns(DnsBase):
    SETTING_KEYS = ['backend', 'db', 'user', 'name']

    def __init__(self, settings):
        self.logger = logging.getLogger(__name__)
        self.settings = settings
        self.doc = None
        self.domain_id = None
        self.domain = None
        if hasattr(settings, 'powerdns_backend') and (
           settings.powerdns_backend == 'sqlite'):
            self._conn = sqlite3.connect(settings.powerdns_db)
            self._cursor = self._conn.cursor()
        else:
            raise Exception("can't get database connection")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._conn.close()

    def _db(self, sql):
        error = None
        # print(sql)
        try:
            self.logger.debug(sql)
            self._cursor.execute(sql)
            self._conn.commit()
        except:
            error = "%s\n\n" % sql
            error += traceback.format_exc()
            self.logger.error(error)

        # print(error)
        return (error, self._cursor)

    def check_domain(self, domain):
        error, result = self._db(
            'SELECT id FROM domains WHERE name="{}"'.format(domain)
        )
        lookup_domain = result.fetchone()
        has_domain = True if lookup_domain else False
        return has_domain

    def set_domain(self, domain, new=False):
        self.domain = domain
        if not new:
            error, result = self._db(
                'SELECT id FROM domains WHERE name="{}"'.format(domain)
            )
            self.domain_id = result.fetchone()[0]

    def _calc_serial(self, previous=""):
        serial_date = time.strftime("%Y%m%d", time.localtime())
        if not previous or not previous.startswith(serial_date):
            return "{}{}".format(serial_date, "00")
        serial_number = int(previous[8:10])
        serial_number += 1
        return "{}{:02d}".format(serial_date, serial_number)

    def add_soa(self):
        serial = self._calc_serial(previous=None)
        self.add_record(
            self.domain,
            SOA_FORMAT.format(serial=serial, **self.doc),
            rtype="SOA",
            ttl=self.get_ttl(self.doc)
        )

    def get_soa_serial(self):
        error, result = self._db(
            '''SELECT content FROM records WHERE name="{}"
               AND type="SOA"'''.format(self.domain)
        )
        soa = result.fetchone()[0]
        try:
            current_serial = soa.split(" ")[2]
        except IndexError:
            current_serial = ""
        return current_serial

    def update_soa(self, domain=None, serial=None):
        if domain:
            self.set_domain(domain)
        if not serial:
            serial = self.get_soa_serial()

        new_soa = SOA_FORMAT.format(serial=self._calc_serial(serial), **self.doc)
        self.update_record(
            self.domain, new_soa,
            rtype="SOA", ttl=self.get_ttl(self.doc)
        )
        # TODO sudoers
        #os.system("pdns_control purge {}$".format(self.domain))

    def add_domain(self, domain=None):
        if domain:
            self.set_domain(domain, new=True)
        error, result = self._db("""INSERT INTO domains (name, type)
                    VALUES ('{}', 'NATIVE')""".format(self.domain))
        self.domain_id = self._cursor.lastrowid
        self.add_soa()

    def del_domain(self, domain=None):
        if domain:
            self.set_domain(domain)
        error, result = self._db(
            "DELETE FROM records WHERE domain_id={}".format(self.domain_id)
        )
        error, result = self._db("DELETE FROM domains WHERE id={}".format(self.domain_id))

    def del_domains(self):
        error, result = self._db("DELETE FROM records")
        error, result = self._db("DELETE FROM domains")

    def _prepare_record_value(self, value):
        if hasattr(value, 'startswith') and value.startswith('$ip_'):  # get ip value from hashmap
            value = self.lookup_map[value]
        return value

    def add_record(self, key, value, rtype='A', ttl=3600,
                   priority='NULL', domain=None):
        # print('add_record', 'key:"%s", value:"%s", rtype:"%s", domain:"%s"' % (key, value, rtype, domain or self.domain))
        if domain:
            self.set_domain(domain)
        priority = 'NULL'
        value_sql = None

        # MX
        # print('test MX')
        if rtype.upper() == 'MX':
            key = self.domain
            value_sql = value['host']
            priority=int(value['priority'])

        # SRV
        # print('test SRV')
        if rtype.upper() == 'SRV':
            value_sql = "{weight} {port} {targethost}".format(**value)
            priority=int(value['priority'])

        value_sql = self._prepare_record_value(value_sql or value)
        sql = """
        INSERT INTO records
            (domain_id, name, content, type, ttl, prio)
        VALUES
            ({domain_id},'{key}','{value}','{rtype}',{ttl},{priority})
        """.format(
            domain_id=self.domain_id,
            key=key, value=value_sql,
            rtype=rtype, ttl=ttl, priority=priority
        )
        error, result = self._db(sql)

    def update_record(self, key, value, rtype='A', ttl=3600,
                      priority='NULL', domain=None, lookup='key'):
        if domain:
            self.set_domain(domain)
        # TOOD set ttl
        value = self._prepare_record_value(value)
        if lookup == 'key':
            where = "name='{}'".format(key)
        elif lookup == 'value':
            where = "content='{}'".format(value)
        sql = """
        UPDATE records
        SET domain_id={domain_id}, name='{key}', content='{value}',
            ttl={ttl}, prio={priority}
        WHERE {lookup} AND type='{rtype}'
        """.format(
            domain_id=self.domain_id, key=key, value=value,
            rtype=rtype, ttl=ttl, priority=priority, lookup=where
        )
        error, result = self._db(sql)

    def del_record(self, key, value, rtype='A', domain=None):
        if domain:
            self.set_domain(domain)
        sql = """
        DELETE FROM records
            WHERE name='{key}' AND type='{rtype}'
        """.format(
            domain_id=self.domain_id, key=key,
            value=value, rtype=rtype
        )
        error, result = self._db(sql)

    def _value_trans(self, value_id, rtype=None, item=None):
        if ',' in value_id:
            value = {}
            for v in value_id.split(','):
                value[v] = item[v]
        else:
            if 'value_trans' in rtype:
                value = rtype['value_trans'](
                    item[value_id], self.domain
                )
            else:
                value = item[value_id]
        return value

    def _create_records(self, only_rtype=None):
        for rtype in self.structure:
            name, key_id, value_id = (
                rtype['name'], rtype['key_id'], rtype['value_id']
            )
            # print('name:"%s", key_id:"%s", value_id:"%s"' % (name, key_id, value_id))
            if name in self.doc and (not only_rtype or name == only_rtype):
                for item in self.doc[name]:  # TODO merge with create logic
                    # do key/value transformations
                    if 'key_trans' in rtype:
                        key = rtype['key_trans'](item[key_id], self.domain)
                    else:
                        key = item[key_id]

                    # special case for multi value ids
                    value = self._value_trans(value_id, rtype=rtype, item=item)

                    self.add_record(
                        key, value, rtype=name.upper(), ttl=self.get_ttl(self.doc)
                    )

    def del_records(self, rtype, domain=None):
        if domain:
            self.set_domain(domain)
        error, result = self._db(
            """DELETE FROM records
               WHERE domain_id='{domain_id}' AND type='{rtype}'
            """.format(domain_id=self.domain_id, rtype=rtype.upper())
        )

    def _key_trans(self, key, rtype=None):
        if 'key_trans' in rtype:
            key = rtype['key_trans'](key, self.domain)
        return key

    def create(self):
        was_sucessfull = False
        if self.doc:
            self.set_domain(self.doc['domain'], new=True)
            self.add_domain()
            for nameserver in self.doc['nameservers']:
                self.add_record(self.domain, nameserver, rtype="NS",
                                ttl=self.get_ttl(self.doc))
            self._create_records()
            was_sucessfull = True
        return was_sucessfull

    def update(self):
        was_sucessfull = False
        if self.doc:
            self.set_domain(self.doc['domain'])

        if self.diff:
            # TODO nameserver record
            for rtype in self.structure:
                name, key_id, value_id = (
                    rtype['name'], rtype['key_id'], rtype['value_id']
                )
                # print('name:"%s", key_id:"%s", value_id:"%s"' % (name, key_id, value_id))
                remove, append = [], []

                # remove records
                if name in self.diff['remove']:
                    remove = self.diff['remove'][name]
                    for item in remove:
                        key = self._key_trans(item[key_id], rtype=rtype)
                        value = self._value_trans(value_id, rtype=rtype, item=item)
                        self.del_record(key, value, rtype=name.upper())

                # update/reset records
                if name in self.diff['update']:
                    self.del_records(rtype=name)
                    self._create_records(only_rtype=name)

                # new records only needed without update/reset records
                elif name in self.diff['append']:
                    append = self.diff['append'][name]
                    for item in append:
                        key = self._key_trans(item[key_id], rtype=rtype)
                        value = self._value_trans(value_id, rtype=rtype, item=item)
                        self.add_record(
                            key, value, rtype=name.upper(), ttl=self.get_ttl(self.doc)
                        )
            self.update_soa()
            was_sucessfull = True
        return was_sucessfull

    def delete(self):
        was_sucessfull = False
        if self.doc:
            self.del_domain(self.doc['domain'])
            was_sucessfull = True
        return was_sucessfull

    def get_domains(self):
        error, result = self._db(
            "SELECT name FROM domains"
        )
        domains = [d[0] for d in result.fetchall()]
        return domains

    def get_records(self, domain):
        error, result = self._db(
            "SELECT id FROM domains WHERE name='%s'" % domain
        )
        domain_id = result.fetchone()[0]
        error, result = self._db(
            """SELECT type, name, content
            FROM records WHERE domain_id=%s
            ORDER by type, name, content""" % domain_id
        )
        records = OrderedDict([
            ('a', []),
            ('aaaa', []),
            ('cname', []),
            ('mx', []),
            ('ns', []),
            ('txt', []),
            ('srv', []),
        ])
        for row in result.fetchall():
            rtype, key, value = row
            key = reverse_fqdn(domain, key)
            if rtype.lower() in ['cname', 'mx', 'ns', 'txt', 'srv']:
                value = reverse_fqdn(domain, value)

            if rtype.lower() in records:
                records[rtype.lower()].append((key, value))
        return records
