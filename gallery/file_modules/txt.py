import os
from wand.image import Image
from wand.color import Color
from wand.font import Font

from gallery.file_modules import FileModule
from gallery.util import hash_file

class TXTFile(FileModule):

    def __init__(self, file_path, dir_path):
        FileModule.__init__(self, file_path, dir_path)
        self.mime_type = "text/plain"

        self.generate_thumbnail()

    def generate_thumbnail(self):
        self.thumbnail_uuid = hash_file(self.file_path) + ".jpg"

        with Image(background=Color('#EEEEEE'), width=256, height=256) as bg:
            with open(self.file_path, encoding='utf-8', errors='ignore') as f:
                text = f.read()
                if len(text) > 512:
                    text = text[0:512]
                font = Font(path="Arial",size=20,color=Color('#333333'))
                bg.caption(text=text,left=10,top=10,font=font)
                bg.save(filename=os.path.join(self.dir_path,
                        self.thumbnail_uuid))
