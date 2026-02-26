import os
from PIL import Image as PILImage
import pillow_heif

from gallery.file_modules import FileModule
from gallery.util import hash_file

pillow_heif.register_heif_opener()

class HEICFile(FileModule):
    def __init__(self, file_path, dir_path):
        FileModule.__init__(self, file_path, dir_path)
        self.mime_type = "image/heic"

        self.generate_thumbnail()

    def generate_thumbnail(self):
        self.thumbnail_uuid = hash_file(self.file_path) + ".jpg"

        thumb_path = os.path.join(self.dir_path, self.thumbnail_uuid)

        img = PILImage.open(self.file_path).convert("RGB")

        size = min(img.width, img.height)
        left = (img.width - size) // 2
        top = (img.height - size) // 2
        img = img.crop((left, top, left + size, top + size))

        img = img.resize((256, 256))
        img.save(thumb_path, "JPEG")