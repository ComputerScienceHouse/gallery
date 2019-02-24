from gallery.file_modules import FileModule


class PDFFile(FileModule):

    def __init__(self, file_path, dir_path):
        FileModule.__init__(self, file_path, dir_path)
        self.mime_type = "application/pdf"

        self.generate_thumbnail()
