from addict import Dict  # type: ignore
from flask import session
from functools import wraps
from typing import Any, Callable, Dict, List, Union
import hashlib
import os

from gallery.models import Directory, File, Tag, Administration
from gallery import ldap, db

DEFAULT_THUMBNAIL_NAME = 'reedphoto'
ROOT_DIR_ID = 1


def get_dir_file_contents(dir_id: int) -> List[File]:
    contents = [f for f in File.query.filter(File.parent == dir_id).all()]
    contents.sort(key=lambda x: x.get_name())
    contents.sort(key=lambda x: x.date_uploaded)
    return contents


def get_full_dir_path(dir_id: int) -> str:
    path_stack = []
    dir_model = Directory.query.filter(Directory.id == dir_id).first()
    path_stack.append(dir_model.name)
    while dir_model.parent is not None:
        dir_model = Directory.query.filter(Directory.id == dir_model.parent).first()
        path_stack.append(dir_model.name)
    path_stack.pop()
    path = ""

    while not len(path_stack) == 0:
        path = os.path.join(path, path_stack.pop())

    return os.path.join('/', path)


def convert_bytes_to_utf8(dic: Dict[Any, Any]) -> Dict[Any, Any]:
    for key in dic:
        if isinstance(key, bytes):
            try:
                k = key.decode('utf-8')
            except Exception as e:
                print(e)
            v = dic[key]
            del dic[key]
            dic[k] = v
        if isinstance(dic[key], bytes):
            try:
                v = dic[key].decode('utf-8')
            except Exception as e:
                print(e)
            dic[key] = v
    return dic


def get_files_tagged(uuids: List[str]) -> List[File]:
    # NOTE(rossdylan): I think this is what was originally intended for this
    # function. It was seriously broken so I rewrote it from scratch
    fids = Tag.query(Tag.file_id).filter(Tag.uid in uuids).all()
    return File.query.filter(File.id in fids).all()


def get_lockdown_status():
    admin = Administration.query.first()
    return admin.lockdown


def gallery_auth(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapped_function(*args: Any, **kwargs: Any) -> Any:
        uuid = str(session.get('userinfo', {}).get('uuid', ''))
        uid = str(session.get('userinfo', {}).get('preferred_username', ''))
        name = ldap.convert_uuid_to_displayname(uuid)
        is_eboard = ldap.is_eboard(uid)
        is_rtp = ldap.is_rtp(uid)
        is_alumni = ldap.is_alumni(uid)
        is_organizer = ldap.is_organizer(uid)

        # NOTE(rossdylan): This is probably a more precise type than we need,
        # if different data is needed just expand the value type to Any
        auth_dict: Dict[str, Union[str, bool]] = {}
        auth_dict['uuid'] = uuid
        auth_dict['uid'] = uid
        auth_dict['name'] = name
        auth_dict['is_eboard'] = is_eboard
        auth_dict['is_rtp'] = is_rtp
        auth_dict['is_alumni'] = is_alumni
        auth_dict['is_organizer'] = is_organizer
        kwargs['auth_dict'] = auth_dict
        return func(*args, **kwargs)
    return wrapped_function


def hash_file(fname: str) -> str:
    m = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            m.update(chunk)
    return m.hexdigest()
