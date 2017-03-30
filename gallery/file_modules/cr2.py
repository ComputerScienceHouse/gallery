import os
import piexif
import subprocess
from wand.image import Image
from wand.color import Color

from gallery.file_modules import FileModule
from gallery.util import hash_file

class CR2File(FileModule):

    def __init__(self, file_path):
        FileModule.__init__(self, self.convert_to_jpg(file_path))
        self.file_type = "Photo"
        self.load_exif()
        self.generate_thumbnail()


    def load_exif(self):
        print("LOAD EXIF")
        self.exif_dict = piexif.load(self.file_path)


    def generate_thumbnail(self):
        print("GEN THUMB")
        self.thumbnail_uuid = hash_file(self.file_path)

        with Image(filename=self.file_path) as img:
            with img.clone() as image:
                size = image.width if image.width < image.height else image.height
                image.crop(width=size, height=size, gravity='center')
                image.resize(256, 256)
                image.background_color = Color("#EEEEEE")
                image.format = 'jpeg'
                image.save(filename=os.path.join("/gallery-data/thumbnails",
                    self.thumbnail_uuid))

    def convert_to_jpg(self, _file_path):
        # wand convert from cr2 to jpeg remove cr2 file
        old_file_path = _file_path
        file_path = os.path.splitext(_file_path)[0]
        subprocess.check_output(['dcraw',
                                 '-w',
                                 old_file_path])
        subprocess.check_output(['convert',
                                 file_path + ".ppm",
                                 file_path + ".jpg"])
        # rm the old file
        os.remove(old_file_path)
        # rm the ppm transitional file
        os.remove(file_path + ".ppm")
        # final jpg
        return file_path + ".jpg"
