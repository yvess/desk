# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from desk.pluginbase.dns import DnsBase
import sqlite3


"""

INSERT INTO domains (name, type) values ('test.com', 'NATIVE');
INSERT INTO records (domain_id, name, content, type,ttl,prio) VALUES (1,'test.com','localhost ahu@ds9a.nl 1','SOA',86400,NULL);
INSERT INTO records (domain_id, name, content, type,ttl,prio) VALUES (1,'test.com','dns-us1.powerdns.net','NS',86400,NULL);
INSERT INTO records (domain_id, name, content, type,ttl,prio) VALUES (1,'test.com','dns-eu1.powerdns.net','NS',86400,NULL);
INSERT INTO records (domain_id, name, content, type,ttl,prio) VALUES (1,'www.test.com','199.198.197.196','A',120,NULL);
INSERT INTO records (domain_id, name, content, type,ttl,prio) VALUES (1,'mail.test.com','195.194.193.192','A',120,NULL);
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
            self.conn = sqlite3.connect(settings.powerdns_db)
            self.cursor = self.conn.cursor()
        else:
            raise Exception("can't init database")

    def add_domain(self, domain):
        print("adding domain")
        self.cursor.execute("INSERT INTO domains (name, type) values ('{}', 'NATIVE')".format(domain))
        self.domain_id = self.cursor.lastrowid

    def add_record(self, key, value, type='A', ttl=86400, prio='NULL'):
        if self.domain_id:
            self.cursor.execute(
                """INSERT INTO records (domain_id, name, content, type, ttl, prio)
                   VALUES (self.domain_id,'{key}','{value}','{type}',{ttl},{prio})""".format(
                    key=key, value=value, type=type, ttl=ttl, prio=prio
                )
            )

    def create(self):
        sucess = False
        if self.doc:
            self.add_domain(self.doc['domain'])
            for nameserver in [n.strip() for n in self.doc['nameservers'].split(",")]:
                self.add_record(nameserver, self.doc['domain'], nameserver, type="NS")
            self.conn.commit()
 	
        return sucess

    def update(self):
        print("update")
