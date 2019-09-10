from datetime import datetime

import flask_sqlalchemy  # type: ignore
from sqlalchemy import Text, String, Integer, Boolean, ForeignKey, DateTime, Column

from gallery import db

strfformat = "%Y-%m-%d"

_base: flask_sqlalchemy.Model = db.Model


class Directory(_base):
    __tablename__ = 'directories'
    id = Column(Integer, primary_key=True)
    parent = Column(ForeignKey('directories.id'))  # type: ignore
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

    def date(self):
        return self.date_uploaded.strftime(strfformat)

    def get_name(self):
        return self.title or self.name


class File(_base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True)
    parent = Column(ForeignKey('directories.id'), nullable=False)  # type: ignore
    name = Column(Text, nullable=False)
    title = Column(Text)
    caption = Column(Text, nullable=False)
    date_uploaded = Column(DateTime, nullable=False)
    author = Column(Text, nullable=False)
    thumbnail_uuid = Column(Text, nullable=False)
    mimetype = Column(Text, nullable=False)
    exif_data = Column(Text, nullable=False)
    hidden = Column(Boolean, nullable=True)
    s3_id = Column(String(32))  # MD5 sums are always 32 chars long

    def __init__(self, parent, name, caption,
                 author, thumbnail_uuid,
                 mimetype, exif_data, s3_id):
        self.parent = parent
        self.name = name
        self.caption = caption
        self.date_uploaded = datetime.now()
        self.author = author
        self.thumbnail_uuid = thumbnail_uuid
        self.mimetype = mimetype
        self.exif_data = exif_data
        self.s3_id = s3_id

    def date(self):
        return self.date_uploaded.strftime(strfformat)

    def get_name(self):
        return self.title or self.name


class Tag(_base):
    __tablename__ = 'tags'
    file_id = Column(ForeignKey('files.id'), primary_key=True)  # type: ignore
    uuid = Column(Text, primary_key=True)

    def __init__(self, file_id, uuid):
        self.file_id = file_id
        self.uuid = uuid


class Administration(_base):
    __tablename__ = 'admin'
    lockdown = Column(Boolean, nullable=True)
