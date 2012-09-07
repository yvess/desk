# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from desk.plugin.dns import DnsBase
import sqlite3


"""

INSERT INTO domains (name, type) values ('test.com', 'NATIVE');
INSERT INTO records (domain_id, name, content, type,ttl,prio) VALUES (1,'test.com','localhost ahu@ds9a.nl 1','SOA',86400,NULL);
INSERT INTO records (domain_id, name, content, type,ttl,prio) VALUES (1,'test.com','dns-us1.powerdns.net','NS',86400,NULL);
INSERT INTO records (domain_id, name, content, type,ttl,prio) VALUES (1,'test.com','dns-eu1.powerdns.net','NS',86400,NULL);
INSERT INTO records (domain_id, name, content, type,ttl,prio) VALUES (1,'www.test.com','199.198.197.196','A',120,NULL);
INSERT INTO records (domain_id, name, content, type,ttl,priority) VALUES (1,'mail.test.com','195.194.193.192','A',120,NULL);
INSERT INTO records (domain_id, name, content, type,ttl,prio) VALUES (1,'localhost.test.com','127.0.0.1','A',120,NULL);
INSERT INTO records (domain_id, name, content, type,ttl,prio) VALUES (1,'test.com','mail.test.com','MX',120,25);

"""


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

    def _db(self, sql):
        try:
            self._cursor.execute(sql)
        except sqlite3.IntegrityError:
            raise Exception("db database problem")

    def add_domain(self, domain):
        self._db("INSERT INTO domains (name, type) VALUES ('{}', 'NATIVE')".format(domain))
        self.domain_id = self._cursor.lastrowid
        self.add_record(domain, 'localhost y@yas.ch 1', rtype="SOA")  # TODO: where to put SOA?
        

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

    def create(self):
        sucess = False
        domain = self.doc['domain']  # TODO put in init
        if self.doc:
            self.add_domain(domain)
            for nameserver in [n.strip() for n in self.doc['nameservers'].split(",")]:
                self.add_record(domain, nameserver, rtype="NS")
            for a in self.doc['a']:
                self.add_record(".".join([a['host'], domain]), a['ip'], rtype="A")  # TODO add special case for main @ domain?
            for cname in self.doc['cname']:
                self.add_record(".".join([cname['alias'], domain]), cname['host'], rtype="CNAME")
            for mx in self.doc['mx']:
                self.add_record(domain, mx['host'], priority=int(mx['priority']), rtype="MX")
            self._conn.commit()
        return sucess

    def update(self):
        print("update")
