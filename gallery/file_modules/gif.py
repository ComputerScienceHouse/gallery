import os

from wand.image import Image

from gallery.file_modules import FileModule
from gallery.util import hash_file

MAX_FILE_SIZE = 5000000


class GIFFile(FileModule):
    def __init__(self, file_path):
        FileModule.__init__(self, file_path)
        self.mime_type = "image/gif"

        self.generate_thumbnail()

    def generate_thumbnail(self):
        self.thumbnail_uuid = hash_file(self.file_path) + ".gif"

        with Image(filename=self.file_path) as img:
            size = img.width if img.width < img.height else img.height
            img.crop(width=size, height=size, gravity='center')
            img.resize(256, 256)
            img.format = 'gif'
            img.save(filename=os.path.join("/gallery-data/thumbnails", self.thumbnail_uuid))

        # If the file size is over 5mb, save jpeg thumbnail instead
        if os.path.getsize(os.path.join("/gallery-data/thumbnails", self.thumbnail_uuid)) > MAX_FILE_SIZE:
            super()
