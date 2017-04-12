import os

from gallery.file_modules import FileModule
from gallery.util import hash_file

class PDFFile(FileModule):

    def __init__(self, file_path):
        FileModule.__init__(self, file_path)
        self.mime_type = "application/pdf"
