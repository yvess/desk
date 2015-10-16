# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from desk.plugin.extcrm.extcrmbase import ExtCrmBase


class Dummy(ExtCrmBase):
    def get_address(self, pk=None):
        address = {
            'company_title': "Muster AG",
            'firstname': "Hans",
            'lastname': "Müller",
            'address_street': "Meine Strasse 5",
            'country_iso_alpha2': "CH",
            'address_zip': "8000",
            'address_city': "Zürich"
        }
        return address
