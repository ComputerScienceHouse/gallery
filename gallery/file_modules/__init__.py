import magic
import os
from typing import Any, Dict, List, Optional
from wand.image import Image
from wand.color import Color

from gallery.util import DEFAULT_THUMBNAIL_NAME
from gallery.util import hash_file
from gallery.util import convert_bytes_to_utf8


class FileModule(object):
    file_path: Optional[str] = None
    dir_path: Optional[str] = None
    exif_dict: Dict[str, Any] = {'Exif': {}}
    mime_type: Optional[str] = None
    thumbnail_uuid: str = DEFAULT_THUMBNAIL_NAME
    file_name: Optional[str] = None

    def __init__(self, file_path: str, dir_path: str):
        print("BASE CONSTRUCTOR")
        self.file_path = file_path
        self.file_name = file_path.split('/')[-1]
        self.dir_path = dir_path

    def get_exif(self) -> Dict[str, Any]:
        return convert_bytes_to_utf8(self.exif_dict['Exif'])

    def get_type(self) -> Optional[str]:
        return self.mime_type

    def get_thumbnail(self) -> str:
        return self.thumbnail_uuid

    def get_name(self) -> Optional[str]:
        return self.file_name

    def generate_thumbnail(self):
        self.thumbnail_uuid = hash_file(self.file_path)

        with Image(filename=self.file_path) as img:
            with Image(width=img.width, height=img.height,
                    background=Color("#EEEEEE")) as bg:
                bg.composite(img, 0, 0)
                size = img.width if img.width < img.height else img.height
                bg.crop(width=size, height=size, gravity='center')
                bg.resize(256, 256)
                bg.format = 'jpeg'
                bg.save(filename=os.path.join(self.dir_path,
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
from gallery.file_modules.mp3 import MP3File

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
    "text/plain": TXTFile,
    "audio/mpeg": MP3File
}


# classism
def parse_file_info(file_path: str, dir_path: str) -> Optional[FileModule]:
    print("entering parse_file_info")
    mime_type = magic.from_file(file_path, mime=True)
    print(mime_type)
    print(file_path)
    if mime_type in file_mimetype_relation:
        return file_mimetype_relation[mime_type](file_path, dir_path)

    return None


def supported_mimetypes() -> List[str]:
    return [m for m in file_mimetype_relation.keys()]


def generate_image_thumbnail(file_path: str, dir_path: str, mime_type: str) -> Optional[str]:
    module = file_mimetype_relation[mime_type]
    return module(file_path, dir_path).get_thumbnail()
