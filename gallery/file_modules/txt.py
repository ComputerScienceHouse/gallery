import os

from gallery.file_modules import FileModule
from gallery.util import hash_file

class TXTFile(FileModule):

    def __init__(self, file_path):
        FileModule.__init__(self, file_path)
        self.mime_type = "text/plain"
