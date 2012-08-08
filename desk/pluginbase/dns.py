# coding: utf-8
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function

import abc


class DnsBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def create(self):
        """Create the dns record."""

    @abc.abstractmethod
    def update(self, record):
        """Update the dns record."""
