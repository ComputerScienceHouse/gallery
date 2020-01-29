import inspect
import json
import os
import zipfile
import re
import subprocess
import tempfile

from datetime import timedelta
from sys import stderr
from typing import Any, Dict, Optional, List, Union, cast

from alembic import command
import click
from csh_ldap import CSHLDAP
from flask import Flask
from flask import config
from flask import current_app
from flask import jsonify
from flask import redirect
from flask import request
from flask import url_for
from flask import render_template
from flask import session
from flask import send_from_directory
from flask import abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from sqlalchemy.sql import func as sql_func
from sqlalchemy.orm import load_only
from flask_pyoidc.flask_pyoidc import OIDCAuthentication
from flask_pyoidc.provider_configuration import (
    ProviderConfiguration,
    ClientMetadata,
)
from gallery._version import __version__, BUILD_REFERENCE, COMMIT_HASH
from gallery.file_store import (S3Storage, LocalStorage, FileStorage)
from gallery.ldap import LDAPWrapper
import flask_migrate
import requests
from werkzeug import secure_filename

app = Flask(__name__)
app.config.update({
    "SQLALCHEMY_TRACK_NOTIFICATIONS": False,
    "VERSION": __version__,
    "BUILD_REFERENCE": BUILD_REFERENCE,
    "COMMIT_HASH": COMMIT_HASH
})


# NOTE(rossdylan): the types are imprecise here due to something in flask
# so we manually cast it to the config type.
app_config: config.Config = cast(config.Config, app.config)
if os.path.exists(os.path.join(os.getcwd(), "config.py")):
    app_config.from_pyfile(os.path.join(os.getcwd(), "config.py"))
else:
    app_config.from_pyfile(os.path.join(os.getcwd(), "config.env.py"))
app.config.update(app_config)

db: SQLAlchemy = SQLAlchemy(app)
migrate = flask_migrate.Migrate(app, db)

# Disable SSL certificate verification warning
requests.packages.urllib3.disable_warnings()

auth = OIDCAuthentication({
    'default': ProviderConfiguration(
        issuer=app_config['OIDC_ISSUER'],
        client_metadata=ClientMetadata(
            client_id=app_config['OIDC_CLIENT_ID'],
            client_secret=app_config['OIDC_CLIENT_SECRET']
        )
    )
}, app)

if "LDAP_BIND_DN" in app.config:
    ldap = LDAPWrapper(CSHLDAP(
        app.config['LDAP_BIND_DN'],
        app.config['LDAP_BIND_PW'],
    ))
else:
    ldap = LDAPWrapper(
        None,
        app.config.get("EBOARD_UIDS", "").split(","),
        app.config.get("RTP_UIDS", "").split(","),
    )

app.add_template_global(ldap, name="ldap")

storage_interface: FileStorage
if "LOCAL_STORAGE_PATH" in app.config:
    storage_interface = LocalStorage(app)
elif "S3_URI" in app.config:
    storage_interface = S3Storage(app)
else:
    raise Exception("Please configure a storage provider")

# pylint: disable=C0413
from gallery.models import Directory, Administration
from gallery.models import File
from gallery.models import Tag

from gallery.util import DEFAULT_THUMBNAIL_NAME
from gallery.util import ROOT_DIR_ID
from gallery.util import get_dir_file_contents
from gallery.util import get_full_dir_path
from gallery.util import convert_bytes_to_utf8
from gallery.util import gallery_auth
from gallery.util import get_files_tagged

from gallery.file_modules import parse_file_info
from gallery.file_modules import generate_image_thumbnail
from gallery.file_modules import supported_mimetypes
from gallery.file_modules import FileModule


@app.route("/")
@auth.oidc_auth('default')
def index():
    root_id = get_dir_tree(internal=True)
    return redirect("/view/dir/" + str(root_id['id']))


@app.route('/upload', methods=['GET'])
@auth.oidc_auth('default')
@gallery_auth
def view_upload(auth_dict: Optional[Dict[str, Any]] = None):
    if request.referrer is None:
        return redirect("/")
    dir_filter = re.compile(r".*\/view\/dir\/(\d*)")
    dir_search = dir_filter.search(request.referrer)
    file_filter = re.compile(r".*\/view\/file\/(\d*)")
    file_search = file_filter.search(request.referrer)
    if dir_search:
        dir_id = int(dir_search.group(1))
    elif file_search:
        file_id = int(file_search.group(1))
        dir_id = File.query.filter(File.id == file_id).first().parent
    else:
        return redirect("/")
    return render_template("upload.html",
                           auth_dict=auth_dict,
                           dir_id=dir_id)


@app.route('/upload', methods=['POST'])
@auth.oidc_auth('default')
@gallery_auth
def upload_file(auth_dict: Optional[Dict[str, Any]] = None):
    # Dropzone multi file is broke with .getlist()
    uploaded_files = [t[1] for t in request.files.items()]

    assert auth_dict is not None
    owner = auth_dict['uuid']

    # hardcoding is bad
    parent = request.form.get('parent_id')

    # Create return object
    # NOTE(rossdylan): We split out the errors and success into their own
    # variables so we don't have to do funky casting
    upload_status: Dict[str, Union[str, List[str], List[Dict[str, Any]]]] = {}
    upload_status['redirect'] = "/view/dir/" + str(parent)
    errors: List[str] = []
    success: List[Dict[str, Any]] = []

    for upload in uploaded_files:
        filename = secure_filename(upload.filename)
        file_model = File.query.filter(File.parent == parent) \
                               .filter(File.name == filename).first()
        if file_model is None:
            dir_path = tempfile.mkdtemp()
            filepath = os.path.join(dir_path, filename)
            upload.save(filepath)

            assert filename
            assert dir_path
            assert parent
            assert owner
            file_model = add_file(filename, dir_path, parent, "", owner)

            # Upload File
            file_stat = os.stat(filepath)
            with open(filepath, "rb") as f_hnd:
                storage_interface.put(
                    "files/{}".format(file_model.s3_id),
                    f_hnd
                )
            os.remove(filepath)

            # Upload Thumbnail
            filepath = os.path.join(dir_path, file_model.thumbnail_uuid)
            file_stat = os.stat(filepath)
            with open(filepath, "rb") as f_hnd:
                storage_interface.put(
                    "thumbnails/" + file_model.s3_id,
                    f_hnd,
                )
            os.remove(filepath)
            os.rmdir(dir_path)
            if file_model is None:
                errors.append(filename)
                continue

            success.append(
                {
                    "name": file_model.name,
                    "id": file_model.id
                })
        else:
            errors.append(filename)

    upload_status['error'] = errors
    upload_status['success'] = success

    refresh_default_thumbnails()
    # actually redirect to URL
    # change from FORM post to AJAX maybe?
    return jsonify(upload_status)


@app.route('/create_folder', methods=['GET'])
@auth.oidc_auth('default')
@gallery_auth
def view_mkdir(auth_dict: Optional[Dict[str, Any]] = None):
    if request.referrer is None:
        return redirect("/")

    dir_filter = re.compile(r".*\/view\/dir\/(\d*)")
    dir_search = dir_filter.search(request.referrer)
    file_filter = re.compile(r".*\/view\/file\/(\d*)")
    file_search = file_filter.search(request.referrer)
    if dir_search:
        dir_id = int(dir_search.group(1))
    elif file_search:
        file_id = int(file_search.group(1))
        dir_id = File.query.filter(File.id == file_id).first().parent
    else:
        return redirect("/")
    return render_template("mkdir.html",
                           auth_dict=auth_dict,
                           dir_id=dir_id)


@app.route('/jump_dir', methods=['GET'])
@auth.oidc_auth('default')
@gallery_auth
def view_jumpdir(auth_dict: Optional[Dict[str, Any]] = None):
    gallery_lockdown = util.get_lockdown_status()
    if gallery_lockdown and (not auth_dict['is_eboard'] and not auth_dict['is_rtp']):
        abort(405)
    return render_template("jumpdir.html",
                           auth_dict=auth_dict)


@app.route('/api/mkdir', methods=['POST'])
@auth.oidc_auth('default')
@gallery_auth
def api_mkdir(
    internal: bool = False,
    parent_id: Optional[str] = None,
    dir_name: Optional[str] = None,
    owner: Optional[str] = None,
    auth_dict: Optional[Dict[str, Any]] = None
):

    assert auth_dict is not None
    owner = auth_dict['uuid']

    # hardcoding is bad
    parent_id = request.form.get('parent_id')

    # TODO: Validate all the params coming in
    dir_name = request.form.get("dir_name")
    assert dir_name is not None
    file_path = os.path.join('/', dir_name)

    upload_status: Dict[str, Union[str, List[str], List[Dict[str, Any]]]] = {}
    error: List[str] = []
    success: List[Dict[str, Any]] = []

    # Sometimes we want to put things in their place
    if file_path != "" and file_path != "/":
        path = file_path.split('/')
        path.pop(0) # remove blank

        # now put these dirs in the db
        for directory in path:
            # ignore dir//dir patterns
            if directory == "":
                continue

            # We really need better validation at some point
            assert parent_id
            assert directory
            assert owner
            parent_id = add_directory(parent_id, directory, "", owner)
            if parent_id is None:
                error.append(directory)
            else:
                success.append(
                    {
                        "name": directory,
                        "id": parent_id
                    })

    # Create return object
    upload_status['redirect'] = "/view/dir/" + str(parent_id)
    upload_status['error'] = error
    upload_status['success'] = success
    return jsonify(upload_status)


@app.cli.command()
def refresh_thumbnails():
    click.echo("Refreshing thumbnails")
    refresh_default_thumbnails()


@app.cli.command()
def init_root():
    click.echo("Initializing root directory")
    # Ensure that we have a root directory
    # XXX there's definitely a better way to do this, I don't have access to the
    # docs right now since I'm on a plane, but I'd wager the SQLAlchemy has a way to
    # get the number of rows in a table without retrieving them (especially since
    # Postgres definitely support this)
    if len([d for d in Directory.query.all()]) == 0:
        root_dir = Directory(None, "Gallery!",
                            "A Multimedia Gallery Written in Python with Flask!",
                            "root", DEFAULT_THUMBNAIL_NAME, "{\"g\":[]}")
        db.session.add(root_dir)
        db.session.flush()
        db.session.commit()

        # Upload the default thumbnail photo to S3 if it's not already up there
        # XXX it's probably a good idea to move this outside of the root directory
        # creation check. That way if a deployment is given incorrect S3 credentials
        # when the root directory is created we can still recover from the case
        # where there is not default thumbnail
        default_thumbnail_path = "thumbnails/" + DEFAULT_THUMBNAIL_NAME + ".jpg"

        with open(default_thumbnail_path, "rb") as f_hnd:
            storage_interface.put(
                "files/{}".format(DEFAULT_THUMBNAIL_NAME),
                f_hnd,
            )


def add_directory(parent_id: str, name: str, description: str, owner: str):
    dir_siblings = Directory.query.filter(Directory.parent == parent_id).all()
    for sibling in dir_siblings:
        if sibling.get_name() == name:
            return None

    uuid_thumbnail = DEFAULT_THUMBNAIL_NAME
    dir_model = Directory(parent_id, name, description, owner,
                          uuid_thumbnail, "{\"g\":[]}")
    db.session.add(dir_model)
    db.session.flush()
    db.session.commit()
    db.session.refresh(dir_model)

    return dir_model.id


def add_file(file_name: str, path: str, dir_id: str, description: str, owner: str) -> Optional[File]:
    file_path = os.path.join('/', path, file_name)

    file_data = parse_file_info(file_path, path)
    if file_data is None:
        return None

    file_model = File(
        dir_id,
        file_data.get_name(),
        description,
        owner,
        file_data.get_thumbnail(),
        file_data.get_type(),
        json.dumps(file_data.get_exif()),
        # NOTE(rossdylan): Default thumbnails come from the FileModule base
        file_data.get_thumbnail().split(".")[0],
    )
    db.session.add(file_model)
    db.session.flush()
    db.session.commit()
    db.session.refresh(file_model)
    return file_model


def refresh_directory_thumbnail(dir_model: Directory) -> str:
    dir_children = [d for d in Directory.query.filter(Directory.parent == dir_model.id).all()]
    file_children = [f for f in File.query.filter(File.parent == dir_model.id).all()]
    for file in file_children:
        if file.thumbnail_uuid != DEFAULT_THUMBNAIL_NAME and not file.hidden:
            return file.thumbnail_uuid
    for d in dir_children:
        if d.thumbnail_uuid != DEFAULT_THUMBNAIL_NAME:
            return d.thumbnail_uuid
    # WE HAVE TO GO DEEPER (inception noise)
    for d in dir_children:
        # TODO: Switch to iterative tree walk using a queue to avoid
        # recursion issues with super large directory structures
        return refresh_directory_thumbnail(d)
    # No thumbnail found
    return DEFAULT_THUMBNAIL_NAME


def refresh_default_thumbnails():
    missing_thumbnails = File.query.filter(File.thumbnail_uuid == DEFAULT_THUMBNAIL_NAME).all()
    for file_model in missing_thumbnails:
        dir_path = get_full_dir_path(file_model.parent)
        file_path = os.path.join(dir_path, file_model.name)
        mime = file_model.mimetype
        file_model.thumbnail_uuid = generate_image_thumbnail(file_path, dir_path, mime)
        db.session.flush()
        db.session.commit()
        db.session.refresh(file_model)

    missing_thumbnails = Directory.query.filter(Directory.thumbnail_uuid == DEFAULT_THUMBNAIL_NAME).all()
    for dir_model in missing_thumbnails:
        dir_model.thumbnail_uuid = refresh_directory_thumbnail(dir_model)
        db.session.flush()
        db.session.commit()
        db.session.refresh(dir_model)


@app.route("/api/file/delete/<int:file_id>", methods=['POST'])
@auth.oidc_auth('default')
@gallery_auth
def delete_file(file_id: int, auth_dict: Optional[Dict[str, Any]] = None):
    file_model = File.query.filter(File.id == file_id).first()

    if file_model is None:
        return "file not found", 404

    assert auth_dict
    if not (auth_dict['is_eboard']
            or auth_dict['is_rtp']
            or auth_dict['uuid'] == file_model.author):
        return "Permission denied", 403

    if File.query.filter(
        File.id != file_model.id
                ).filter(
        File.s3_id == file_model.s3_id
                ).first() is None:

        storage_interface.remove(
            "files/" + file_model.s3_id,
        )
        storage_interface.remove(
            "thumbnails/" + file_model.s3_id,
        )

    current_tags = Tag.query.filter(Tag.file_id == file_id).all()
    for tag in current_tags:
        db.session.delete(tag)
    db.session.delete(file_model)
    db.session.flush()
    db.session.commit()

    return "ok", 200


@app.route("/api/file/hide/<int:file_id>", methods=['POST'])
@auth.oidc_auth('default')
@gallery_auth
def hide_file(file_id: int, auth_dict: Optional[Dict[str, Any]] = None):
    file_model = File.query.filter(File.id == file_id).first()

    if file_model is None:
        return "file not found", 404

    assert auth_dict
    if not (auth_dict['is_eboard']
            or auth_dict['is_rtp']
            or auth_dict['uuid'] == file_model.author):
        return "Permission denied", 403

    file_model.hidden = True

    # Remove image from thumbnails
    dirs = Directory.query.filter(or_(Directory.thumbnail_uuid == file_model.thumbnail_uuid, \
        Directory.thumbnail_uuid == file_model.thumbnail_uuid[:-4]))
    for d in dirs:
        d.thumbnail_uuid = refresh_directory_thumbnail(d)

    db.session.flush()
    db.session.commit()

    return "ok", 200


@app.route("/api/file/show/<int:file_id>", methods=['POST'])
@auth.oidc_auth('default')
@gallery_auth
def show_file(file_id: int, auth_dict: Optional[Dict[str, Any]] = None):
    file_model = File.query.filter(File.id == file_id).first()

    if file_model is None:
        return "file not found", 404

    assert auth_dict
    if not (auth_dict['is_eboard']
            or auth_dict['is_rtp']):
        return "Permission denied", 403

    file_model.hidden = False

    # Add image as directory thumbnail
    parent_model = Directory.query.filter(Directory.id == file_model.parent).first()
    if parent_model.thumbnail_uuid == DEFAULT_THUMBNAIL_NAME:
        parent_model.thumbnail_uuid = refresh_directory_thumbnail(parent_model)

    db.session.flush()
    db.session.commit()

    return "ok", 200


@app.route("/api/dir/delete/<int:dir_id>", methods=['POST'])
@auth.oidc_auth('default')
@gallery_auth
def delete_dir(dir_id: int, auth_dict: Optional[Dict[str, Any]] = None):
    dir_model = Directory.query.filter(Directory.id == dir_id).first()

    if dir_model is None:
        return "dir not found", 404
    if dir_model.id <= ROOT_DIR_ID:
        return "Permission denied", 403

    assert auth_dict
    if not (auth_dict['is_eboard']
            or auth_dict['is_rtp']
            or auth_dict['uuid'] == dir_model.author):
        return "Permission denied", 403

    dirs = [d for d in Directory.query.filter(Directory.parent == dir_id).all()]
    files = [f for f in File.query.filter(File.parent == dir_id).all()]

    for child_dir in dirs:
        delete_dir(child_dir.id)

    for child_file in files:
        delete_file(child_file.id)

    if len(dir_model.thumbnail_uuid.split('.')) > 1:
        dir_path = get_full_dir_path(dir_model.id)
        os.rmdir(dir_path)
    db.session.delete(dir_model)
    db.session.flush()
    db.session.commit()

    return "ok", 200


@app.route("/api/file/move/<int:file_id>", methods=['POST'])
@auth.oidc_auth('default')
@gallery_auth
def move_file(file_id: int, auth_dict: Optional[Dict[str, Any]] = None):
    file_model = File.query.filter(File.id == file_id).first()

    if file_model is None:
        return "file not found", 404

    parent = request.form.get('parent')

    assert auth_dict
    if not (auth_dict['is_eboard']
            or auth_dict['is_rtp']
            or auth_dict['uuid'] == file_model.author):
        return "Permission denied", 403

    File.query.filter(File.id == file_id).update({
        'parent': parent
    })
    db.session.flush()
    db.session.commit()

    return "ok", 200


@app.route("/api/dir/move/<int:dir_id>", methods=['POST'])
@auth.oidc_auth('default')
@gallery_auth
def move_dir(dir_id: int, auth_dict: Optional[Dict[str, Any]] = None):
    dir_model = Directory.query.filter(Directory.id == dir_id).first()

    if dir_model is None:
        return "dir not found", 404

    parent = request.form.get('parent')

    assert auth_dict
    if not (auth_dict['is_eboard']
            or auth_dict['is_rtp']
            or auth_dict['uuid'] == dir_model.author):
        return "Permission denied", 403

    Directory.query.filter(Directory.id == dir_id).update({
        'parent': parent
    })
    db.session.flush()
    db.session.commit()

    return "ok", 200


@app.route("/api/admin/lockdown", methods=['POST'])
@auth.oidc_auth('default')
@gallery_auth
def gallery_lockdown(auth_dict: Optional[Dict[str, Any]] = None):
    assert auth_dict
    if not (auth_dict['is_eboard']
            or auth_dict['is_rtp']):
        return "Permission denied", 403

    admin = Administration.query.first()
    admin.lockdown = not admin.lockdown

    db.session.flush()
    db.session.commit()

    return "ok", 200


@app.route("/api/file/rename/<int:file_id>", methods=['POST'])
@auth.oidc_auth('default')
def rename_file(file_id: int):
    file_model = File.query.filter(File.id == file_id).first()

    if file_model is None:
        return "file not found", 404

    title = request.form.get('title')

    File.query.filter(File.id == file_id).update({
        'title': title
    })
    db.session.flush()
    db.session.commit()

    return "ok", 200


@app.route("/api/dir/rename/<int:dir_id>", methods=['POST'])
@auth.oidc_auth('default')
def rename_dir(dir_id: int):
    dir_model = Directory.query.filter(Directory.id == dir_id).first()

    if dir_model is None:
        return "dir not found", 404

    title = request.form.get('title')

    Directory.query.filter(Directory.id == dir_id).update({
        'title': title
    })
    db.session.flush()
    db.session.commit()

    return "ok", 200


@app.route("/api/file/describe/<int:file_id>", methods=['POST'])
@auth.oidc_auth('default')
def describe_file(file_id: int):
    file_model = File.query.filter(File.id == file_id).first()

    if file_model is None:
        return "file not found", 404

    caption = request.form.get('caption')
    if caption is None or caption == "":
        return "please enter a caption", 400

    File.query.filter(File.id == file_id).update({
        'caption': caption
    })
    db.session.flush()
    db.session.commit()

    return "ok", 200


@app.route("/api/dir/describe/<int:dir_id>", methods=['POST'])
@auth.oidc_auth('default')
def describe_dir(dir_id: int):
    dir_model = Directory.query.filter(Directory.id == dir_id).first()

    if dir_model is None:
        return "dir not found", 404

    desc = request.form.get('description')

    Directory.query.filter(Directory.id == dir_id).update({
        'description': desc
    })
    db.session.flush()
    db.session.commit()

    return "ok", 200


@app.route("/api/file/tag/<int:file_id>", methods=['POST'])
@auth.oidc_auth('default')
def tag_file(file_id: int):
    file_id = int(file_id)
    file_model = File.query.filter(File.id == file_id).first()

    if file_model is None:
        return "file not found", 404

    current_tags = Tag.query.filter(Tag.file_id == file_id).all()
    for tag in current_tags:
        db.session.delete(tag)
        db.session.flush()
        db.session.commit()

    uuids = json.loads(request.form.get('members', '[]'))

    for uuid in uuids:
        # Don't allow empty tag entries
        if uuid != '':
            tag_model = Tag(file_id, uuid)
            db.session.add(tag_model)
            db.session.flush()
            db.session.commit()
            db.session.refresh(tag_model)

    return "ok", 200


@app.route("/api/file/get/<int:file_id>")
@auth.oidc_auth('default')
@gallery_auth
def display_file(file_id: int, auth_dict: Optional[Dict[str, Any]] = None):
    gallery_lockdown = util.get_lockdown_status()
    if gallery_lockdown and (not auth_dict['is_eboard'] and not auth_dict['is_rtp']):
        abort(405)

    file_model = File.query.filter(File.id == file_id).first()

    if file_model is None:
        return "file not found", 404

    link = storage_interface.get_link("files/{}".format(file_model.s3_id))
    return redirect(link)


@app.route("/api/thumbnail/get/<int:file_id>")
@auth.oidc_auth('default')
@gallery_auth
def display_thumbnail(file_id: int, auth_dict: Optional[Dict[str, Any]] = None):
    gallery_lockdown = util.get_lockdown_status()
    if gallery_lockdown and (not auth_dict['is_eboard'] and not auth_dict['is_rtp']):
        abort(405)

    file_model = File.query.filter(File.id == file_id).first()

    link = storage_interface.get_link("thumbnails/{}".format(file_model.s3_id))
    return redirect(link)


@app.route("/api/thumbnail/get/dir/<int:dir_id>")
@auth.oidc_auth('default')
@gallery_auth
def display_dir_thumbnail(dir_id: int, auth_dict: Optional[Dict[str, Any]] = None):
    gallery_lockdown = util.get_lockdown_status()
    if gallery_lockdown and (not auth_dict['is_eboard'] and not auth_dict['is_rtp']):
        abort(405)

    dir_model = Directory.query.filter(Directory.id == dir_id).first()

    thumbnail_uuid = dir_model.thumbnail_uuid
    # let's make this a bit more nuanced for the transition
    if len(thumbnail_uuid.split('.')) > 1:
        thumbnail_uuid = thumbnail_uuid.split('.')[0]

    link = storage_interface.get_link("thumbnails/{}".format(thumbnail_uuid))
    return redirect(link)


@app.route("/api/file/next/<int:file_id>")
@auth.oidc_auth('default')
def get_file_next_id(file_id: int, internal: bool = False):
    file_model = File.query.filter(File.id == file_id).first()
    files = [f.id for f in get_dir_file_contents(file_model.parent)]

    idx = files.index(file_id) + 1

    if idx >= len(files):
        idx = -1
    else:
        idx = files[idx]

    if internal:
        return idx
    return jsonify({"index": idx})


@app.route("/api/file/prev/<int:file_id>")
@auth.oidc_auth('default')
def get_file_prev_id(file_id: int, internal: bool = False):
    file_model = File.query.filter(File.id == file_id).first()
    files = [f.id for f in get_dir_file_contents(file_model.parent)]

    idx = files.index(file_id) - 1

    if idx < 0:
        idx = -1
    else:
        idx = files[idx]

    if internal:
        return idx
    return jsonify({"index": idx})


@app.route("/api/get_supported_mimetypes")
@auth.oidc_auth('default')
def get_supported_mimetypes():
    return jsonify({"mimetypes": supported_mimetypes()})


@app.route("/api/get_dir_tree")
@auth.oidc_auth('default')
@gallery_auth
def get_dir_tree(internal: bool = False, auth_dict: Optional[Dict[str, Any]] = None):
    gallery_lockdown = util.get_lockdown_status()
    if gallery_lockdown and (not auth_dict['is_eboard'] and not auth_dict['is_rtp']):
        abort(405)

    # TODO: Convert to iterative tree traversal using a queue to avoid
    # recursion issues with large directory structures
    def get_dir_children(dir_id: int) -> Any:
        dirs = [d for d in Directory.query.filter(Directory.parent == dir_id).all()]
        children = []
        for child in dirs:
            children.append({
                'name': child.get_name(),
                'id': child.id,
                'children': get_dir_children(child.id)
                })
        children.sort(key=lambda x: x['name'])
        return children

    root = Directory.query.filter(Directory.parent == None).first()

    tree = {}

    tree['name'] = root.get_name()
    tree['id'] = root.id
    tree['children'] = get_dir_children(root.id)

    # return after gallery-data
    if internal:
        return tree
    else:
        return jsonify(tree)


@app.route("/api/directory/get/<int:dir_id>")
@auth.oidc_auth('default')
@gallery_auth
def display_files(dir_id: int, internal: bool = False, auth_dict: Optional[Dict[str, Any]] = None):
    gallery_lockdown = util.get_lockdown_status()
    if gallery_lockdown and (not auth_dict['is_eboard'] and not auth_dict['is_rtp']):
        abort(405)

    file_list = [("File", f) for f in File.query.filter(File.parent == dir_id).all()]
    dir_list = [("Directory", d) for d in Directory.query.filter(Directory.parent == dir_id).all()]

    # Sort by name/title
    file_list.sort(key=lambda x: x[1].get_name())
    file_list.sort(key=lambda x: x[1].date_uploaded)
    dir_list.sort(key=lambda x: x[1].get_name())
    dir_list.sort(key=lambda x: x[1].date_uploaded)

    ret_dict = dir_list + file_list
    if internal:
        return ret_dict
    return jsonify(ret_dict)


@app.route("/api/directory/get_parent/<int:dir_id>", methods=['GET'])
@auth.oidc_auth('default')
def get_dir_parent(dir_id: int):
    dir_model = Directory.query.filter(Directory.id == dir_id).first()
    print("Dir name: " + dir_model.get_name())
    print("Dir's Parent: " + str(dir_model.parent))
    return dir_model.parent


@app.route("/api/file/get_parent/<int:file_id>", methods=['GET'])
@auth.oidc_auth('default')
def get_file_parent(file_id: int):
    file_model = File.query.filter(File.id == file_id).first()
    print("File name: " + file_model.get_name())
    print("File's Parent: " + str(file_model.parent))
    return file_model.parent


@app.route("/view/dir/<int:dir_id>")
@auth.oidc_auth('default')
@gallery_auth
def render_dir(dir_id: int, auth_dict: Optional[Dict[str, Any]] = None):
    dir_id = int(dir_id)
    if dir_id < ROOT_DIR_ID:
        return redirect('/view/dir/'+ str(ROOT_DIR_ID))
    gallery_lockdown = util.get_lockdown_status()
    if gallery_lockdown and (not auth_dict['is_eboard'] and not auth_dict['is_rtp']):
        abort(405)

    children = display_files(dir_id, internal=True)
    dir_model = Directory.query.filter(Directory.id == dir_id).first()
    if dir_model is None:
        abort(404)
    description = dir_model.description
    display_description = len(description) > 0

    display_parent = True
    if dir_model is None or dir_model.parent is None or dir_id == ROOT_DIR_ID:
        display_parent = False
    path_stack = []
    dir_model_breadcrumbs = dir_model
    path_stack.append(dir_model_breadcrumbs)
    while dir_model_breadcrumbs.parent is not None:
        dir_model_breadcrumbs = Directory.query.filter(Directory.id == dir_model_breadcrumbs.parent).first()
        path_stack.append(dir_model_breadcrumbs)
    path_stack.reverse()

    assert auth_dict
    auth_dict['can_edit'] = (
        auth_dict['is_eboard'] or
        auth_dict['is_rtp'] or
        auth_dict['uuid'] == dir_model.author
    )

    return render_template("view_dir.html",
                           children=children,
                           directory=dir_model,
                           parent=dir_model.parent,
                           parents=path_stack,
                           display_parent=display_parent,
                           description=description,
                           display_description=display_description,
                           auth_dict=auth_dict,
                           lockdown=gallery_lockdown)


@app.route("/view/file/<int:file_id>")
@auth.oidc_auth('default')
@gallery_auth
def render_file(file_id: int, auth_dict: Optional[Dict[str, Any]] = None):
    file_model = File.query.filter(File.id == file_id).first()
    if file_model is None:
        abort(404)
    if file_model.hidden and (not auth_dict['is_eboard'] and not auth_dict['is_rtp'] and not auth_dict['is_alumni']):
        abort(404)
    gallery_lockdown = util.get_lockdown_status()
    if gallery_lockdown and (not auth_dict['is_eboard'] and not auth_dict['is_rtp']):
        abort(405)

    description = file_model.caption
    display_description = len(description) > 0
    display_parent = True
    if file_model is None or file_model.parent is None:
        display_parent = False
    path_stack = []
    path_stack.append(file_model)
    dir_model = file_model
    while dir_model.parent is not None:
        dir_model = Directory.query.filter(Directory.id == dir_model.parent).first()
        path_stack.append(dir_model)
    path_stack.reverse()

    assert auth_dict
    auth_dict['can_edit'] = (
        auth_dict['is_eboard'] or
        auth_dict['is_rtp'] or
        auth_dict['uuid'] == file_model.author
    )
    tags = [tag.uuid for tag in Tag.query.filter(Tag.file_id == file_id).all()]
    return render_template("view_file.html",
                           file_id=file_id,
                           file=file_model,
                           parent=file_model.parent,
                           parents=path_stack,
                           next_file=get_file_next_id(file_id, internal=True),
                           prev_file=get_file_prev_id(file_id, internal=True),
                           display_parent=display_parent,
                           description=description,
                           display_description=display_description,
                           tags=tags,
                           auth_dict=auth_dict,
                           lockdown=gallery_lockdown)


@app.route("/view/random_file")
@auth.oidc_auth('default')
def get_random_file():
    file_model = File.query.order_by(sql_func.random()).first()
    return redirect("/view/file/" + str(file_model.id))


@app.route("/view/filtered")
@auth.oidc_auth('default')
@gallery_auth
def view_filtered(auth_dict: Optional[Dict[str, Any]] = None):
    uuids = request.args.get('uuids', '').split('+')
    files = get_files_tagged(uuids)
    return render_template("view_filtered.html",
                           files=files,
                           uuids=uuids,
                           auth_dict=auth_dict)


@app.route("/api/memberlist")
@auth.oidc_auth('default')
@gallery_auth
def get_member_list(auth_dict: Optional[Dict[str, Any]] = None):
    gallery_lockdown = util.get_lockdown_status()
    if gallery_lockdown and (not auth_dict['is_eboard'] and not auth_dict['is_rtp']):
        abort(405)

    return jsonify(ldap.get_members())


@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(500)
@gallery_auth
def route_errors(error: Any, auth_dict: Optional[Dict[str, Any]] = None):
    if isinstance(error, int):
        code = error
    elif hasattr(error, 'code'):
        code = error.code
    else:
        code = 500

    if code == 404:
        error_desc = "Page Not Found"
    elif code == 405:
        error_desc = "Gallery is currently unavailable"
    else:
        error_desc = type(error).__name__

    return render_template('errors.html',
                           error=error_desc,
                           error_code=code,
                           auth_dict=auth_dict), int(code)


@app.route("/logout")
@auth.oidc_logout
def logout():
    return redirect(url_for('index'), 302)
