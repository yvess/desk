# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from desk.plugin.extcrm.extcrmbase import ExtCrmBase, ContactBase
import pymysql


class TodoyuContact(ContactBase):
    def __init__(self, data):
        self.data = data

    @property
    def name(self):
        return "%s %s" % (self.data['firstname'], self.data['lastname'])

    @property
    def email(self):
        return self.data['contactinfo_info']

    def __unicode__(self):
        return self.data['p_id']


class Todoyu(ExtCrmBase):
    def __init__(self, settings):
        self._address_map = {}
        self._contact_map = {}
        self.settings = settings
        self._fill_maps()

    def _fill_address(self, cursor):
        person = (
            'IFNULL(person_privat.id, person.id) as p_id',
            'IFNULL(person_privat.salutation, person.salutation) as salutation',
            'IFNULL(person_privat.firstname, person.firstname) as firstname',
            'IFNULL(person_privat.lastname, person.lastname) as lastname',
        )
        person_fields = ('p_id', 'salutation', 'firstname', 'lastname')
        address = (
            'address.id_addresstype', 'country.iso_alpha2',
            'address.street', 'address.postbox', 'address.city',
            'address.region', 'address.zip',
            'address.ext_projectbilling_invoicedepartement',
        )
        company = 'company.id', 'company.title'

        SQL = """
        SELECT
        {address}, {person}, {company}
        FROM ext_contact_address as address
        LEFT JOIN (ext_contact_mm_company_address as c2a, ext_contact_company as company)
            ON (address.id=c2a.id_address AND company.id=c2a.id_company)
        LEFT JOIN (ext_contact_mm_person_address as p2a, ext_contact_person as person_privat)
            ON (address.id=p2a.id_address AND person_privat.id=p2a.id_person)
        LEFT JOIN (ext_contact_mm_company_person as c2p, ext_contact_person as person)
            ON (person.id=c2p.id_person AND company.id=c2p.id_company)
        LEFT JOIN (static_country as country)
            ON (address.id_country=country.id)
        WHERE 1
        AND (address.deleted=0)
        AND (company.deleted=0 OR company.deleted IS NULL)
        AND (person.deleted=0 OR person.deleted IS NULL)
        AND (person_privat.deleted=0 OR person_privat.deleted IS NULL)
        ORDER BY
        company.title, firstname, lastname;
        """.format(
            company=", ".join(company),
            person=", ".join(person),
            address=", ".join(address)
        )

        cursor.execute(SQL)
        for r in cursor.fetchall():
            fields = [f.replace('.', '_') for f in (address + person_fields + company)]
            data = dict(zip(fields, r))
            pk_keys = (data['p_id'], 'p'), (data['company_id'], 'c')
            pk = "-".join(["%s%s" % (key, pk) for pk, key in pk_keys if pk])
            if pk:
                if (pk not in self._address_map) or (
                   data['address_id_addresstype'] == 3):  # 3=billing address
                    self._address_map[pk] = data
                elif data['address_id_addresstype'] == 2:  # 2=normal address
                    pass
                else:
                    print("*** double company", data, self._address_map[pk])

    def _fill_contact(self, cursor):
        contactinfo = ('contactinfo.info',)
        person = (
            'person.id as p_id', 'person.salutation as salutation',
            'person.firstname as firstname', 'person.lastname as lastname',
        )
        person_fields = 'p_id', 'salutation', 'firstname', 'lastname',

        SQL = """
        SELECT
            {contactinfo},
            {person}
        FROM ext_contact_contactinfo as contactinfo
        RIGHT JOIN (ext_contact_mm_person_contactinfo as p2c, ext_contact_person as person)
            ON (contactinfo.id=p2c.id_contactinfo AND person.id=p2c.id_person)
        LEFT JOIN ext_contact_mm_company_person as c2p
            ON (person.id=c2p.id_person)
        WHERE 1
        AND (contactinfo.deleted=0) AND (contactinfo.id_contactinfotype=1)
        AND (person.deleted=0 OR person.deleted IS NULL)

        ORDER BY
        p_id, firstname, lastname
        """.format(
            person=", ".join(person),
            contactinfo=", ".join(contactinfo)
        )

        cursor.execute(SQL)
        for item in cursor.fetchall():
            fields = [f.replace('.', '_') for f in (contactinfo + person_fields)]
            data = dict(zip(fields, item))
            pk = "p%s" % data['p_id']
            if pk:
                if (pk not in self._contact_map):
                    self._contact_map[pk] = TodoyuContact(data)
                else:
                    print("*** double contact", data, self._contact_map[pk])

    def _fill_maps(self):
        conn = pymysql.connect(
            host=self.settings.todoyu_host, user=self.settings.todoyu_user,
            passwd=self.settings.todoyu_password, db=self.settings.todoyu_db,
            charset='utf8'
        )
        cursor = conn.cursor()

        self._fill_address(cursor)
        self._fill_contact(cursor)

        cursor.close()
        conn.close()

    def get_address(self, pk=None):
        try:
            return self._address_map[pk]
        except KeyError:
            print(self._address_map.keys())
            print("key error", pk)
            raise KeyError

    def get_contact(self, pk=None):
        return self._contact_map[pk]

    def has_contact(self, pk=None):
        return True if pk in self._contact_map else False
