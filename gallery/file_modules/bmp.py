import os
from wand.image import Image
from wand.color import Color

from gallery.file_modules import FileModule


class BMPFile(FileModule):

    def __init__(self, file_path, dir_path):
        FileModule.__init__(self, file_path, dir_path)
        self.mime_type = "image/bmp"

        self.generate_thumbnail()
