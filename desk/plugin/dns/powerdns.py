# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals

from desk.pluginbase.dns import DnsBase


class Powerdns(DnsBase):
    def create(self):
        print("create")

    def update(self):
        print("update")
