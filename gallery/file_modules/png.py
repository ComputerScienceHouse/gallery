import os
from wand.image import Image
from wand.color import Color

from gallery.file_modules import FileModule
from gallery.util import hash_file


class PNGFile(FileModule):

    def __init__(self, file_path, dir_path):
        FileModule.__init__(self, file_path, dir_path)
        self.mime_type = "image/png"

        self.generate_thumbnail()

    def generate_thumbnail(self):
        self.thumbnail_uuid = hash_file(self.file_path) + ".jpg"

        with Image(filename=self.file_path) as img:
            with Image(width=img.width, height=img.height, background=Color("#EEEEEE")) as bg:
                bg.composite(img, 0, 0)
                size = img.width if img.width < img.height else img.height
                bg.crop(width=size, height=size, gravity='center')
                bg.resize(256, 256)
                bg.format = 'jpeg'
                bg.save(filename=os.path.join(self.dir_path, self.thumbnail_uuid))
