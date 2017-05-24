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
        self.mime_type = "image/x-canon-cr2"
        self.load_exif()
        self.generate_thumbnail()


    def load_exif(self):
        print("LOAD EXIF")
        try:
            self.exif_dict = piexif.load(self.file_path)
        except Exception as e:
            print(e)


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
