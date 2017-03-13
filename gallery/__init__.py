import hashlib
import json
import os
import zipfile
import re
import subprocess

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

app.config["GIT_REVISION"] = subprocess.check_output(['git',
                                                      'rev-parse',
                                                      '--short',
                                                      'HEAD']).decode('utf-8').rstrip()


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

        file_path = os.path.join('/', path, request.form.get('gallery_location'))
        print(path, file=stderr)
        print(request.form.get('gallery-location'), file=stderr)
        print(file_path, file=stderr)

        _, count = re.subn(r'[^a-zA-Z0-9 \/\-\_]', '', file_path)
        if not file_path.startswith("/gallery-data/root") or count != 0:
            return "invalid path" + file_path, 400

        #if file_path == ".":
        #    file_path = ""
        #file_location = os.path.join('/', path, file_path)
        file_location = file_path

        # mkdir -p that shit
        if not os.path.exists(file_location):
            os.makedirs(file_location)

        parent = base_path
        print(base_path, file=stderr)
        print(file_path, file=stderr)
        print(path, file=stderr)
        if file_path.startswith("/" + path):
            file_path = file_path[(len(path) + 1):]
        print(file_path, file=stderr)
        print(file_path.split('/'), file=stderr)
        # Sometimes we want to put things in their place
        if file_path != "" and file_path != "/":
            path = file_path.split('/')
            path.pop(0) # remove blank

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

# @app.route("/preload")
# @auth.oidc_auth
# def preload_images():
#     if not os.path.exists("/gallery-data"):
#         os.makedirs("/gallery-data")
# 
#     r = requests.get("https://csh.rit.edu/~loothelion/test.zip")
#     with open("test.zip", "wb") as archive:
#         archive.write(r.content)
# 
#     with zipfile.ZipFile("test.zip", "r") as zip_file:
#         zip_file.extractall("/gallery-data/")
# 
#     return redirect(url_for("index"), 302)
# 
@app.route("/refreshdb")
@auth.oidc_auth
def refresh_db():
    files = get_dir_tree_dict()
    check_for_dir_db_entry(files, '', None)
    return redirect(url_for("index"), 302)

def check_for_dir_db_entry(dictionary, path, parent_dir):
    uuid_thumbnail = "reedphoto.jpg"

    # check db for this path with parents shiggg
    dir_name = path.split('/')[-1]
    if dir_name == "":
        dir_name = "root"
    dir_model = None
    if parent_dir:
        dir_model = Directory.query.filter(Directory.name == dir_name) \
                                   .filter(Directory.parent == parent_dir.id).first()
    else:
        dir_model = Directory.query.filter(Directory.parent == None).first()

    if dir_model is None:
        # fuck go back this directory doesn't exist as a model
        # we gotta add this shit
        if parent_dir:
            dir_model = Directory(parent_dir.id, dir_name, "", "root",
                                  uuid_thumbnail, "{\"g\":[]}")
        else:
            dir_model = Directory(None, dir_name, "", "root",
                                  uuid_thumbnail, "{\"g\":[]}")
        db.session.add(dir_model)
        db.session.flush()
        db.session.commit()
        db.session.refresh(dir_model)

    # get directory class as dir_model
    for dir_p in dictionary:
        # Don't traverse local files
        if dir_p == '.':
            continue
        check_for_dir_db_entry(
            dictionary[dir_p],
            os.path.join(path, dir_p),
            dir_model)

    for file_p in dictionary['.']:
        # check db for this file path
        file_model = File.query.filter(File.parent == dir_model.id) \
                               .filter(File.name == file_p).first()
        if file_model is None:
            add_file(file_p, path, dir_model.id, "", "root")

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
        if filetype.guess(file_path).mime == "image/x-canon-cr2":
            # wand convert from cr2 to jpeg remove cr2 file
            old_file_path = file_path
            file_path = os.path.splitext(file_path)[0]
            subprocess.check_output(['dcraw',
                                     '-w',
                                     old_file_path])
            subprocess.check_output(['convert',
                                     file_path + ".ppm",
                                     file_path + ".jpg"])
            # rm the old file
            os.remove(old_file_path)
            # rm the ppm transitional file
            os.remove(file_path + ".ppm")
            # final jpg
            file_path = file_path + ".jpg"

        uuid_thumbnail = hash_file(file_path) + ".jpg"
        file_type = "Photo"

        if filetype.guess(file_path).mime == "image/jpeg":
            exif_dict = piexif.load(file_path)

        # add thumbnail
        with Image(filename=file_path) as img:
            with img.clone() as image:
                size = image.width if image.width < image.height else image.height
                image.crop(width=size, height=size, gravity='center')
                image.resize(256, 256)
                image.format = 'jpeg'
                image.save(filename=os.path.join("/gallery-data/thumbnails", uuid_thumbnail))
    elif is_video:
        file_type = "Video"
    exif = json.dumps(convert_bytes_to_utf8(exif_dict['Exif']))

    file_model = File(dir_id, file_path.split('/')[-1], description,
                      owner, uuid_thumbnail, file_type, exif)
    db.session.add(file_model)
    db.session.flush()
    db.session.commit()
    db.session.refresh(file_model)


@app.route("/api/image/get/<int:image_id>")
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

@app.route("/api/thumbnail/get/<int:image_id>")
@auth.oidc_auth
def display_thumbnail(image_id):
    file_model = File.query.filter(File.id == image_id).first()

    if file_model is None:
        return send_from_directory('/gallery-data/thumbnails', 'reedphoto.jpg')

    return send_from_directory('/gallery-data/thumbnails', file_model.thumbnail_uuid)

@app.route("/api/thumbnail/get/dir/<int:dir_id>")
@auth.oidc_auth
def display_dir_thumbnail(dir_id):
    first_child = File.query.filter(File.parent == dir_id).first()

    if first_child is None:
        return send_from_directory('/gallery-data/thumbnails', 'reedphoto.jpg')

    return send_from_directory('/gallery-data/thumbnails', first_child.thumbnail_uuid)

@app.route("/api/image/next/<int:image_id>")
@auth.oidc_auth
def get_image_next_id(image_id, internal=False):
    image_id = int(image_id)
    file_model = File.query.filter(File.id == image_id).first()
    files = [f.id for f in get_dir_file_contents(file_model.parent)]

    idx = files.index(image_id) + 1

    if idx >= len(files):
        idx = -1
    else:
        idx = files[idx]

    if internal:
        return idx
    return jsonify({"index": idx})

@app.route("/api/image/prev/<int:image_id>")
@auth.oidc_auth
def get_image_prev_id(image_id, internal=False):
    image_id = int(image_id)
    file_model = File.query.filter(File.id == image_id).first()
    files = [f.id for f in get_dir_file_contents(file_model.parent)]

    idx = files.index(image_id) - 1

    if idx < 0:
        idx = -1
    else:
        idx = files[idx]

    if internal:
        return idx
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

    # Hardcode gallery name to not be root FIXME
    tree['children'][0]['children'][0]['name'] = "CSH Gallery"

    # return after gallery-data
    if internal:
        return tree['children'][0]['children'][0]
    else:
        return jsonify(tree['children'][0]['children'][0])

@app.route("/api/directory/get/<int:dir_id>")
@auth.oidc_auth
def display_files(dir_id, internal=False):
    file_list = [f for f in File.query.filter(File.parent == dir_id).all()]
    dir_list = [d for d in Directory.query.filter(Directory.parent == dir_id).all()]
    ret_dict = {'directories': dir_list, 'files': file_list}
    if internal:
        return ret_dict
    return jsonify(ret_dict)

@app.route("/view/dir/<int:dir_id>")
@auth.oidc_auth
def render_dir(dir_id):
    if dir_id < 3:
        return redirect('/view/dir/3')

    children = display_files(dir_id, internal=True)
    dir_model = Directory.query.filter(Directory.id == dir_id).first()


    # Hardcode gallery name to not be root FIXME
    if dir_id == 3:
        dir_model.name = "CSH Gallery"

    display_parent = True
    if dir_model is None or dir_model.parent is None or dir_id == 3:
        display_parent = False
    return render_template("view_dir.html",
                           children=children,
                           directory=dir_model,
                           parent=dir_model.parent,
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
                           parent=file_model.parent,
                           next_file=get_image_next_id(file_id, internal=True),
                           prev_file=get_image_prev_id(file_id, internal=True),
                           display_parent=display_parent,
                           username=session['userinfo'].get('preferred_username', ''),
                           display_name=session['userinfo'].get('name', 'CSH Member'))

@app.route("/logout")
@auth.oidc_logout
def logout():
    return redirect(url_for('index'), 302)
