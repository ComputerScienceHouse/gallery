from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import DateTime
from sqlalchemy import Text

from gallery import db

class Directory(db.Model):
    __tablename__ = 'directories'
    id = Column(Integer, primary_key=True)
    parent = Column(ForeignKey('directories.id'))
    name = Column(Text, nullable=False)
    title = Column(Text)
    description = Column(Text, nullable=False)
    date_uploaded = Column(DateTime, nullable=False)
    author = Column(Text, nullable=False)
    thumbnail_uuid = Column(Text, nullable=False)
    blocked_groups = Column(Text, nullable=False)

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
    id = Column(Integer, primary_key=True)
    parent = Column(ForeignKey('directories.id'), nullable=False)
    name = Column(Text, nullable=False)
    title = Column(Text)
    caption = Column(Text, nullable=False)
    date_uploaded = Column(DateTime, nullable=False)
    author = Column(Text, nullable=False)
    thumbnail_uuid = Column(Text, nullable=False)
    mimetype = Column(Text, nullable=False)
    exif_data = Column(Text, nullable=False)

    def __init__(self, parent, name, caption,
                 author, thumbnail_uuid,
                 mimetype, exif_data):
        self.parent = parent
        self.name = name
        self.caption = caption
        self.date_uploaded = datetime.now()
        self.author = author
        self.thumbnail_uuid = thumbnail_uuid
        self.mimetype = mimetype
        self.exif_data = exif_data
