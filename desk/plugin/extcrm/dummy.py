# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
from desk.plugin.extcrm.extcrmbase import ExtCrmBase


class Dummy(ExtCrmBase):
    def get_address(self, pk=None):
        return "dummy address"
