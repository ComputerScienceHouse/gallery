import magic
import os
from wand.image import Image
from wand.color import Color

from gallery.util import hash_file
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

    def generate_thumbnail(self):
        self.thumbnail_uuid = hash_file(self.file_path) + ".jpg"

        with Image(filename=self.file_path) as img:
            with Image(width=img.width, height=img.height,
                    background=Color("#EEEEEE")) as bg:
                bg.composite(img, 0, 0)
                size = img.width if img.width < img.height else img.height
                bg.crop(width=size, height=size, gravity='center')
                bg.resize(256, 256)
                bg.format = 'jpeg'
                bg.save(filename=os.path.join("/gallery-data/thumbnails",
                    self.thumbnail_uuid))


# pylint: disable=C0413
from gallery.file_modules.jpg import JPEGFile
from gallery.file_modules.cr2 import CR2File
from gallery.file_modules.png import PNGFile
from gallery.file_modules.gif import GIFFile
from gallery.file_modules.bmp import BMPFile
from gallery.file_modules.tiff import TIFFFile
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
    "image/bmp": BMPFile,
    "image/x-ms-bmp": BMPFile,
    "image/x-windows-bmp": BMPFile,
    "image/tiff": TIFFFile,
    "image/x-tiff": TIFFFile,
    "video/mp4": MP4File,
    "video/webm": WebMFile,
    "video/ogg": OggFile,
    "application/pdf": PDFFile,
    "text/plain": TXTFile
}

# classism
def parse_file_info(file_path):
    print("entering parse_file_info")
    mime_type = magic.from_file(file_path, mime=True)
    print(mime_type)
    print(file_path)
    if mime_type in file_mimetype_relation:
        return file_mimetype_relation[mime_type](file_path)

    return None

def supported_mimetypes():
    return [m for m in file_mimetype_relation.keys()]
