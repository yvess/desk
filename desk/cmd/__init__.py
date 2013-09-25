# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals, division  # python3
from desk.utils import ObjectDict
import os


class SettingsCommand(object):
    def __init__(self, settings, hostname=os.uname()[1]):
        if isinstance(settings, dict):
            settings = ObjectDict(**settings)
        self.hostname = hostname
        self.settings = settings
