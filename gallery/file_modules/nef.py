import os
import rawpy
import imageio

from gallery.file_modules import FileModule
from gallery.util import hash_file


class NEFFile(FileModule):
    def __init__(self, file_path, dir_path):
        FileModule.__init__(self, file_path, dir_path)
        self.mime_type = "image/x-nikon-nef"

        self.generate_thumbnail()

    def generate_thumbnail(self):
        self.thumbnail_uuid = hash_file(self.file_path) + ".jpg"
        thumb_path = os.path.join(self.dir_path, self.thumbnail_uuid)

        with rawpy.imread(self.file_path) as raw:
            rgb = raw.postprocess(output_bps=8)

            h, w, _ = rgb.shape
            size = min(h, w)
            y = (h - size) // 2
            x = (w - size) // 2
            rgb = rgb[y:y+size, x:x+size]

            imageio.imwrite(thumb_path, rgb)