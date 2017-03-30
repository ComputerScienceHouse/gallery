import filetype

from gallery.util import convert_bytes_to_utf8

class FileModule:
    file_path = None
    exif_dict = {'Exif': {}}
    file_type = None
    thumbnail_uuid = None
    file_name = None

    def __init__(self, file_path):
        print("BASE CONSTRUCTOR")
        self.file_path = file_path
        self.file_name = file_path.split('/')[-1]


    def get_exif(self):
        return convert_bytes_to_utf8(self.exif_dict['Exif'])


    def get_type(self):
        return self.file_type


    def get_thumbnail(self):
        return self.thumbnail_uuid

    def get_name(self):
        return self.file_name


# pylint: disable=C0413
from gallery.file_modules.jpg import JPEGFile

file_mimetype_relation = {
    "image/jpeg": JPEGFile
}

# classism
def parse_file_info(file_path):
    print("entering parse_file_info")
    file_type = filetype.guess(file_path)
    print("mime: " + file_type.mime)

    if file_type.mime in file_mimetype_relation:
        return file_mimetype_relation[file_type.mime](file_path)

    return None
