import os
import piexif
from wand.image import Image
from wand.color import Color

from gallery.file_modules import FileModule
from gallery.util import hash_file

class JPEGFile(FileModule):

    def __init__(self, file_path):
        print("JPEG CONSTRUCTOR")
        FileModule.__init__(self, file_path)
        self.mime_type = "image/jpeg"

        self.load_exif()
        self.generate_thumbnail()


    def load_exif(self):
        print("LOAD EXIF")
        try:
            self.exif_dict = piexif.load(self.file_path)
        except Exception as e:
            print(e)
