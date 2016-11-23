from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import DateTime
from sqlalchemy import Text
from sqlalchemy import Boolean
from sqlalchemy import String

from datetime import datetime

from gallery import db

filetype_enum = Enum('Photo', 'Video', 'Text', name="filetype_enum")

class Directory(db.Model):
    __tablename__ = 'directories'
    id = Column(Integer, primary_key = True)
    parent = Column(ForeignKey('directories.id'))
    name = Column(Text, nullable = False)
    description = Column(Text, nullable = False)
    date_uploaded = Column(DateTime, nullable = False)
    author = Column(Text, nullable = False)
    thumbnail_uuid = Column(Text, nullable = False)
    blocked_groups = Column(Text, nullable = False)

    def __init__(self, parent, name, description,
                 author, thumbnail_uuid, blocked_groups):
        self.parent = parent
        self.name = name
        self.description = description
        self.date_uploaded = datetime.now()
        self.author = author
        self.thumbnail_uuid = thumbnail_uuid
        self.blocked_groups = blocked_groups

class File(db.Model):
    __tablename__ = 'files'
    id = Column(Integer, primary_key = True)
    parent = Column(ForeignKey('directories.id'), nullable = False)
    name = Column(Text, nullable = False)
    caption = Column(Text, nullable = False)
    date_uploaded = Column(DateTime, nullable = False)
    author = Column(Text, nullable = False)
    thumbnail_uuid = Column(Text, nullable = False)
    filetype = Column(filetype_enum, nullable = False)
    exif_data = Column(Text, nullable = False)

    def __init__(self, parent, name, caption,
                 author, thumbnail_uuid,
                 filetype, exif_data):
        self.parent = parent
        self.name = name
        self.caption = caption
        self.date_uploaded = datetime.now()
        self.author = author
        self.thumbnail_uuid = thumbnail_uuid
        self.filetype = filetype
        self.exif_data = exif_data
