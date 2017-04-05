import filetype

from gallery.util import convert_bytes_to_utf8

class FileModule:
    file_path = None
    exif_dict = {'Exif': {}}
    mime_type = None
    thumbnail_uuid = "reedphoto.jpg"
    file_name = None

    def __init__(self, file_path):
        print("BASE CONSTRUCTOR")
        self.file_path = file_path
        self.file_name = file_path.split('/')[-1]


    def get_exif(self):
        return convert_bytes_to_utf8(self.exif_dict['Exif'])


    def get_type(self):
        return self.mime_type


    def get_thumbnail(self):
        return self.thumbnail_uuid

    def get_name(self):
        return self.file_name


# pylint: disable=C0413
from gallery.file_modules.jpg import JPEGFile
from gallery.file_modules.cr2 import CR2File
from gallery.file_modules.png import PNGFile
from gallery.file_modules.gif import GIFFile
from gallery.file_modules.mp4 import MP4File
from gallery.file_modules.webm import WebMFile
from gallery.file_modules.ogg import OggFile
from gallery.file_modules.pdf import PDFFile
from gallery.file_modules.txt import TXTFile

file_mimetype_relation = {
    "image/jpeg": JPEGFile,
    "image/x-canon-cr2": CR2File,
    "image/png": PNGFile,
    "image/gif": GIFFile,
    "video/mp4": MP4File,
    "video/webm": WebMFile,
    "video/ogg": OggFile,
    "application/pdf": PDFFile,
    "text/plain": TXTFile
}

# classism
def parse_file_info(file_path):
    print("entering parse_file_info")
    file_type = filetype.guess(file_path)
    mime_type = None

    if file_type is None:
        mime_type = "text/plain"
    else:
        mime_type = file_type.mime

    if mime_type in file_mimetype_relation:
        return file_mimetype_relation[mime_type](file_path)

    return None
