# coding: utf-8
from __future__ import absolute_import, print_function, division, unicode_literals
import abc


class ExtCrmBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_address(self, pk=None):
        """Return an address from an external crm."""

    @abc.abstractmethod
    def get_contact(self, pk=None):
        """Return an contact from an external crm."""

    @abc.abstractmethod
    def has_contact(self, pk=None):
        """Return true/false it the contact exists"""

class ContactBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def name(self):
        """Return email of contact."""

    @abc.abstractmethod
    def email(self):
        """Return email from contact."""
