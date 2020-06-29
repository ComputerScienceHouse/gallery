import os
from wand.image import Image
from wand.color import Color

from gallery.file_modules import FileModule
from gallery.util import hash_file


class PDFFile(FileModule):

    def __init__(self, file_path, dir_path):
        FileModule.__init__(self, file_path, dir_path)
        self.mime_type = "application/pdf"

        self.generate_thumbnail()

    def generate_thumbnail(self):
        self.thumbnail_uuid = hash_file(self.file_path) + ".jpg"

        with Image(filename=self.file_path, resolution=300) as all_pages:
            with Image(all_pages.sequence[0]) as first_page:
                with Image(width=first_page.width, height=first_page.height,
                        background=Color("#EEEEEE")) as bg:
                    bg.composite(first_page, 0, 0)
                    size = first_page.width if first_page.width < first_page.height else first_page.height
                    bg.crop(width=size, height=size, gravity='north') # top of first page
                    bg.resize(256, 256)
                    bg.format = 'jpeg'
                    bg.save(filename=os.path.join(self.dir_path, self.thumbnail_uuid))
