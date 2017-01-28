import hashlib
import json
import os
import zipfile

from sys import stderr

from alembic import command
import filetype
from flask import Flask
from flask import current_app
from flask import jsonify
from flask import redirect
from flask import request
from flask import url_for
from flask import render_template
from flask import session
from flask import send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_pyoidc.flask_pyoidc import OIDCAuthentication
import flask_migrate
import piexif
import requests
from wand.image import Image
from werkzeug import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_NOTIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = flask_migrate.Migrate(app, db)

# pylint: disable=C0413
from gallery.models import Directory
from gallery.models import File

from gallery.util import allowed_file
from gallery.util import get_dir_file_contents
from gallery.util import get_dir_tree_dict
from gallery.util import convert_bytes_to_utf8


if os.path.exists(os.path.join(os.getcwd(), "config.py")):
    app.config.from_pyfile(os.path.join(os.getcwd(), "config.py"))
else:
    app.config.from_pyfile(os.path.join(os.getcwd(), "config.env.py"))

# Disable SSL certificate verification warning
requests.packages.urllib3.disable_warnings()

auth = OIDCAuthentication(app,
                          issuer=app.config['OIDC_ISSUER'],
                          client_registration_info=app.config['OIDC_CLIENT_CONFIG'])

@app.route("/")
@auth.oidc_auth
def index():
    root_id = get_dir_tree(internal=True)
    return redirect("/view/dir/" + str(root_id['id']))

@app.route('/upload', methods=['GET', 'POST'])
@auth.oidc_auth
def update_file():
    if request.method == 'POST':
        uploaded_files = request.files.getlist("gallery-upload")
        files = []
        owner = str(session['userinfo'].get('sub', ''))

        # hardcoding is bad
        base_path = request.form.get('gallery_dir_id')

        path_stack = []
        dir_model = Directory.query.filter(Directory.id == base_path).first()
        path_stack.append(dir_model.name)
        while dir_model.parent != None:
            dir_model = Directory.query.filter(Directory.id == dir_model.parent).first()
            path_stack.append(dir_model.name)
        path_stack.pop()
        path = ""
        while not len(path_stack) == 0:
            path = os.path.join(path, path_stack.pop())
        file_path = os.path.realpath(os.path.join('/', path, request.form.get('gallery_location')))
        if not file_path.startswith("/gallery-data/root"):
            return "invalid path" + file_path, 400

        if file_path == ".":
            file_path = ""
        file_location = os.path.join('/', path, file_path)

        # mkdir -p that shit
        if not os.path.exists(file_location):
            os.makedirs(file_location)

        parent = base_path

        # Sometimes we want to put things in their place
        if file_path != "":
            path = file_path.split('/')

            # now put these dirs in the db
            for directory in path:
                parent = add_directory(parent, directory, "A new Directory!", owner)

        for upload in uploaded_files:
            if allowed_file(upload.filename):
                filename = secure_filename(upload.filename)
                filepath = os.path.join(file_location, filename)
                upload.save(filepath)

                add_file(filename, file_location, parent, "A New File", owner)
                files.append(filepath)

        return redirect("/view/dir/" + str(parent), 302)
    else:
        return render_template("upload.html",
                                username=session['userinfo'].get('preferred_username', ''),
                                display_name=session['userinfo'].get('name', 'CSH Member'))

def add_directory(parent_id, name, description, owner):
    uuid_thumbnail = "reedphoto.jpg"
    dir_model = Directory(parent_id, name, description, owner,
                          uuid_thumbnail, "{\"g\":[]}")
    db.session.add(dir_model)
    db.session.flush()
    db.session.commit()
    db.session.refresh(dir_model)

    return dir_model.id

def add_file(file_name, path, dir_id, description, owner):
    uuid_thumbnail = "reedphoto.jpg"

    is_image = filetype.image(os.path.join('/', path, file_name)) is not None
    is_video = filetype.video(os.path.join('/', path, file_name)) is not None

    file_path = os.path.join('/', path, file_name)

    def hash_file(fname):
        m = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                m.update(chunk)
        return m.hexdigest()

    exif_dict = {'Exif':{}}
    file_type = "Text"
    if is_image:
        uuid_thumbnail = hash_file(file_path) + ".jpg"
        file_type = "Photo"

        if filetype.guess(file_path).mime == "text/jpeg":
            exif_dict = piexif.load(os.path.join('/', path, file_name))

        # add thumbnail
        with Image(filename=file_path) as img:
            with img.clone() as image:
                image.resize(128, 128)
                image.format = 'jpeg'
                image.save(filename=os.path.join("/gallery-data/thumbnails", uuid_thumbnail))
    elif is_video:
        file_type = "Video"
    exif = json.dumps(convert_bytes_to_utf8(exif_dict['Exif']))

    file_model = File(dir_id, file_name, description,
                      owner, uuid_thumbnail, file_type, exif)
    db.session.add(file_model)
    db.session.flush()
    db.session.commit()
    db.session.refresh(file_model)


@app.route("/api/image/get/<image_id>")
@auth.oidc_auth
def display_image(image_id):
    path_stack = []
    file_model = File.query.filter(File.id == image_id).first()

    if file_model is None:
        return "file not found", 404

    path_stack.append(file_model.name)
    dir_model = Directory.query.filter(Directory.id == file_model.parent).first()
    path_stack.append(dir_model.name)
    while dir_model.parent != None:
        dir_model = Directory.query.filter(Directory.id == dir_model.parent).first()
        path_stack.append(dir_model.name)
    path_stack.pop()
    path = ""
    while not len(path_stack) == 0:
        path = os.path.join(path, path_stack.pop())
    return send_from_directory('/', path)

@app.route("/api/thumbnail/get/<image_id>")
@auth.oidc_auth
def display_thumbnail(image_id):
    file_model = File.query.filter(File.id == image_id).first()

    if file_model is None:
        return send_from_directory('/gallery-data/thumbnails', 'reedphoto.jpg')

    return send_from_directory('/gallery-data/thumbnails', file_model.thumbnail_uuid)

@app.route("/api/thumbnail/get/dir/<dir_id>")
@auth.oidc_auth
def display_dir_thumbnail(dir_id):
    first_child = File.query.filter(File.parent == dir_id).first()

    if first_child is None:
        return send_from_directory('/gallery-data/thumbnails', 'reedphoto.jpg')

    return send_from_directory('/gallery-data/thumbnails', first_child.thumbnail_uuid)

@app.route("/api/image/next/<image_id>")
@auth.oidc_auth
def get_image_next_id(image_id):
    file_model = File.query.filter(File.id == image_id).first()
    files = [f.id for f in get_dir_file_contents(file_model.parent)]

    idx = files.index(image_id) + 1

    if idx >= len(files):
        idx = -1
    else:
        idx = files[idx]

    return jsonify({"index": idx})

@app.route("/api/image/prev/<image_id>")
@auth.oidc_auth
def get_image_prev_id(image_id):
    file_model = File.query.filter(File.id == image_id).first()
    files = [f.id for f in get_dir_file_contents(file_model.parent)]

    idx = files.index(image_id) - 1

    if idx < 0:
        idx = -1
    else:
        idx = files[idx]

    return jsonify({"index": idx})

@app.route("/api/get_dir_tree")
@auth.oidc_auth
def get_dir_tree(internal=False):
    def get_dir_children(dir_id):
        dirs = [d for d in Directory.query.filter(Directory.parent == dir_id).all()]
        children = []
        for child in dirs:
            children.append({
                'name': child.name,
                'id': child.id,
                'children': get_dir_children(child.id)
                })
        return children

    root = dir_model = Directory.query.filter(Directory.parent == None).first()

    tree = {}

    tree['name'] = root.name
    tree['id'] = root.id
    tree['children'] = get_dir_children(root.id)

    # return after gallery-data
    if internal:
        return tree['children'][0]['children'][0]
    else:
        return jsonify(tree['children'][0]['children'][0])

@app.route("/api/directory/get/<dir_id>")
@auth.oidc_auth
def display_files(dir_id, internal=False):
    file_list = [f for f in File.query.filter(File.parent == dir_id).all()]
    dir_list = [d for d in Directory.query.filter(Directory.parent == dir_id).all()]
    ret_dict = {'directories': dir_list, 'files': file_list}
    if internal:
        return ret_dict
    return jsonify(ret_dict)

@app.route("/view/dir/<dir_id>")
@auth.oidc_auth
def render_dir(dir_id):
    children = display_files(dir_id, internal=True)
    dir_model = Directory.query.filter(Directory.id == dir_id).first()
    display_parent = True
    if dir_model is None or dir_model.parent is None:
        display_parent = False
    return render_template("view_dir.html",
                           children=children,
                           directory=dir_model,
                           display_parent=display_parent,
                           username=session['userinfo'].get('preferred_username', ''),
                           display_name=session['userinfo'].get('name', 'CSH Member'))

@app.route("/view/file/<file_id>")
@auth.oidc_auth
def render_file(file_id):
    file_model = File.query.filter(File.id == file_id).first()
    display_parent = True
    if file_model is None or file_model.parent is None:
        display_parent = False
    return render_template("view_file.html",
                           file_id=file_id,
                           file=file_model,
                           display_parent=display_parent,
                           username=session['userinfo'].get('preferred_username', ''),
                           display_name=session['userinfo'].get('name', 'CSH Member'))

@app.route("/logout")
@auth.oidc_logout
def logout():
    return redirect(url_for('index'), 302)
