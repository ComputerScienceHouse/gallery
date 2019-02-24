from gallery.file_modules import FileModule


class TIFFFile(FileModule):

    def __init__(self, file_path, dir_path):
        FileModule.__init__(self, file_path, dir_path)
        self.mime_type = "image/tiff"

        self.generate_thumbnail()
