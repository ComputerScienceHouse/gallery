from gallery.file_modules import FileModule
from gallery.util import DEFAULT_THUMBNAIL_NAME

class MP3File(FileModule):
    def __init__(self, file_path, dir_path):
        FileModule.__init__(self, file_path, dir_path)
        self.mime_type = "audio/mpeg"

        self.generate_thumbnail()
        
    def generate_thumbnail(self):
        self.thumbnail_uuid = DEFAULT_THUMBNAIL_NAME + ".jpg"
