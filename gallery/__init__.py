import json
import os
from sys import stderr

from alembic import command

from flask import Flask
from flask import current_app
from flask import jsonify
from flask import redirect
from flask import url_for
from flask import session
from flask import send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_pyoidc.flask_pyoidc import OIDCAuthentication

import flask_migrate
import filetype
import piexif

import requests

import zipfile

from gallery.util import get_dir_tree_dict
from gallery.util import convert_bytes_to_utf8

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_NOTIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = flask_migrate.Migrate(app, db)

from gallery.models import Directory
from gallery.models import File


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
    return "Hello " + str(session['userinfo'].get('name', ''))

@app.route("/preload")
@auth.oidc_auth
def preload_images():
    if not os.path.exists("images"):
        os.makedirs("images")

    r = requests.get("https://csh.rit.edu/~loothelion/test.zip")
    with open("test.zip", "wb") as archive:
        archive.write(r.content)

    with zipfile.ZipFile("test.zip", "r") as zip_file:
        zip_file.extractall("images/")

    return redirect(url_for("index"), 302)

@app.route("/refreshdb")
@auth.oidc_auth
def refresh_db():
    files = get_dir_tree_dict()
    check_for_dir_db_entry(files, '', None)
    return redirect(url_for("index"), 302)

def check_for_dir_db_entry(dictionary, path, parent_dir):
    UUID_THUMBNAIL = "test123"
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
                                  UUID_THUMBNAIL, "{\"g\":[]}")
        else:
            dir_model = Directory(None, dir_name, "", "root",
                                  UUID_THUMBNAIL, "{\"g\":[]}")
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

def add_file(file_name, path, dir_id, description, owner):
    is_image = filetype.image(os.path.join("images", path, file_name)) is not None
    is_video = filetype.video(os.path.join("images", path, file_name)) is not None

    exif_dict = {'Exif':{}}
    file_type = "Text"
    if is_image:
        file_type = "Photo"
        if filetype.guess(os.path.join("images",
                                       path,
                                       file_name)).mime == "text/jpeg":
            exif_dict = piexif.load(os.path.join("images", path, file_name))
    elif is_video:
        file_type = "Video"
    exif = json.dumps(convert_bytes_to_utf8(exif_dict['Exif']))
    file_model = File(dir_id, file_name, description,
                      owner, UUID_THUMBNAIL, file_type, exif)
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

    return send_from_directory('../images', path)

@app.route("/api/directory/get/<dir_id>")
@auth.oidc_auth
def display_files(dir_id):
    return jsonify([f.id for f in File.query.filter(File.parent == dir_id).all()])

@app.route("/logout")
@auth.oidc_logout
def logout():
    return redirect(url_for('index'), 302)
