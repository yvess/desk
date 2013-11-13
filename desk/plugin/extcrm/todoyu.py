# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from desk.plugin.extcrm.extcrmbase import ExtCrmBase
import pymysql


class Todoyu(ExtCrmBase):
    def __init__(self, settings):
        self.person_map = {}
        self.company_map = {}
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

        SQL_PERSON = """
        SELECT
        {person}, {address}
        FROM ext_contact_person AS person
        CROSS JOIN (ext_contact_mm_person_address as p2a, ext_contact_address as address)
            ON (person.id=p2a.id_person AND address.id=p2a.id_address)
        LEFT JOIN (static_country as country)
            ON (address.id_country=country.id)
        WHERE person.deleted=0
        ORDER BY person.firstname, person.lastname;""".format(
            person=", ".join(person),
            address=", ".join(address)
        )

        SQL_COMPANY = """
        SELECT
        {company}, {person}, {address}
        FROM ext_contact_person AS person
        CROSS JOIN (ext_contact_mm_company_person as c2p, ext_contact_company as company)
            ON (person.id=c2p.id_person AND company.id=c2p.id_company)
        LEFT JOIN (ext_contact_mm_company_address as c2a, ext_contact_address as address)
            ON (company.id=c2a.id_company AND address.id=c2a.id_address)
        LEFT JOIN (static_country as country)
            ON (address.id_country=country.id)
        WHERE company.deleted=0
        ORDER BY person.firstname, person.lastname;""".format(
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

        for SQL, fields, mapping in (
                (SQL_PERSON, person + address, self.person_map),
                (SQL_COMPANY, company + person + address, self.company_map)
        ):
            cur.execute(SQL)
            for r in cur.fetchall():
                fields = [f.replace('.', '_') for f in fields]
                data = dict(zip(fields, r))
                if (data['person_id'] not in mapping) or (
                   data['address_id_addresstype'] == 3):  # 3=billing address
                    mapping[data['person_id']] = data
                elif data['address_id_addresstype'] == 2:  # 2=normal address
                    pass
                else:
                    print("double company", data, mapping[data['person_id']])

        cur.close()
        conn.close()

    def get_address(self, pk=None, kind='person'):
        mapping = getattr(self, '%s_map' % kind)
        return mapping[pk]
