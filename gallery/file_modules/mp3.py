import os
from wand.image import Image

from gallery.file_modules import FileModule
from gallery.util import hash_file

class MP3File(FileModule):
    def __init__(self, file_path, dir_path):
        FileModule.__init__(self, file_path, dir_path)
        self.mime_type = "audio/mpeg"

        self.generate_thumbnail()

    def generate_thumbnail(self):
        self.thumbnail_uuid = hash_file(self.file_path) + ".jpg"

        with Image(filename="thumbnails/reedphoto.jpg") as bg:
                bg.save(filename=os.path.join(self.dir_path, self.thumbnail_uuid))
