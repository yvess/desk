import abc


class ExtCrmBase(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_address(self, pk=None):
        """Return an address from an external crm."""

    @abc.abstractmethod
    def get_contact(self, pk=None):
        """Return an contact from an external crm."""

    @abc.abstractmethod
    def has_contact(self, pk=None):
        """Return true/false it the contact exists"""

class ContactBase(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def name(self):
        """Return email of contact."""

    @abc.abstractmethod
    def email(self):
        """Return email from contact."""
