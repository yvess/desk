from os import mkdir, listdir, path, unlink
import sys
import shutil
import tempfile
from socket import gethostbyaddr
from desk.command import SettingsCommand
from desk.utils import create_order_doc, auth_from_uri
from desk.utils import FilesForCouch
