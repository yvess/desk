# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from desk.plugin.extcrm.extcrmbase import ExtCrmBase
import pymysql


class Todoyu(ExtCrmBase):
    def __init__(self, settings):
        self.address_map = {}
        self.settings = settings
        self._fill_maps()

    def _fill_maps(self):
        person = (
            'person.id', 'person.salutation',
            'person.firstname', 'person.lastname'
        )
        address = (
            'address.id_addresstype', 'country.iso_alpha2',
            'address.street', 'address.postbox', 'address.city',
            'address.region', 'address.zip',
        )
        company = 'company.id', 'company.title'

        SQL = """
        SELECT
        {address}, {person}, {company}
        FROM ext_contact_address as address
        LEFT JOIN (ext_contact_mm_company_address as c2a, ext_contact_company as company)
            ON (address.id=c2a.id_address AND company.id=c2a.id_company)
        LEFT JOIN (ext_contact_mm_company_person as c2p, ext_contact_person as person)
            ON (person.id=c2p.id_person AND company.id=c2p.id_company)
        LEFT JOIN (static_country as country)
            ON (address.id_country=country.id)
        WHERE 1
        AND (address.deleted=0)
        AND (company.deleted=0 OR company.deleted IS NULL) 
        AND (person.deleted=0 OR person.deleted IS NULL)
        ORDER BY company.title, person.firstname, person.lastname;
        """.format(
            company=", ".join(company),
            person=", ".join(person),
            address=", ".join(address)
        )

        conn = pymysql.connect(
            host=self.settings.todoyu_host, user=self.settings.todoyu_user,
            passwd=self.settings.todoyu_password, db=self.settings.todoyu_db,
            charset='utf8'
        )
        cur = conn.cursor()

        cur.execute(SQL)
        for r in cur.fetchall():
            fields = [f.replace('.', '_') for f in (address + person + company)]
            data = dict(zip(fields, r))
            pk_keys = (data['person_id'], 'p'), (data['company_id'], 'c')
            pk = "-".join(["%s%s" % (key, pk) for pk, key in pk_keys if pk])
            if pk:
                if (pk not in self.address_map) or (
                   data['address_id_addresstype'] == 3):  # 3=billing address
                    self.address_map[pk] = data
                elif data['address_id_addresstype'] == 2:  # 2=normal address
                    pass
                else:
                    print("double company", data, self.address_map[data[pk]])

        cur.close()
        conn.close()

    def get_address(self, pk=None):
        return self.address_map[pk]
