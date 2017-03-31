from moviepy.editor import VideoFileClip
import os
import piexif
from wand.image import Image
from wand.color import Color

from gallery.file_modules import FileModule
from gallery.util import hash_file

class OggFile(FileModule):

    def __init__(self, file_path):
        FileModule.__init__(self, file_path)
        self.file_type = "Video"

        self.generate_thumbnail()


    def generate_thumbnail(self):
        self.thumbnail_uuid = hash_file(self.file_path) + ".jpg"
        thumbnail_loc = os.path.join("/gallery-data/thumbnails", self.thumbnail_uuid)

        clip = VideoFileClip(self.file_path)
        time_mark = clip.duration * 0.05
        clip.save_frame(thumbnail_loc, t=time_mark)

        with Image(filename=thumbnail_loc) as img:
            with img.clone() as image:
                size = image.width if image.width < image.height else image.height
                image.crop(width=size, height=size, gravity='center')
                image.resize(256, 256)
                image.background_color = Color("#EEEEEE")
                image.format = 'jpeg'
                image.save(filename=thumbnail_loc)
