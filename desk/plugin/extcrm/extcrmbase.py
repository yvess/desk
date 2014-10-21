# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
import abc


class ExtCrmBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_address(self):
        """Return an address from an external crm."""
