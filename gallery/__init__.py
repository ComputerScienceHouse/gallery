import os

from addict import Dict

from flask import Flask
from flask import redirect
from flask import url_for
from flask import session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_pyoidc.flask_pyoidc import OIDCAuthentication

import requests

import zipfile

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_NOTIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from .models import Directory
from .models import File


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

def check_for_dir_db_entry(dictionary, path, parent_dir):
    # check db for this path with parents shiggg
    print("Directory Path: " + path)

    if parent_dir:
        dir_model = Directory.query.filter(Directory.parent == parent_dir.id and \
                                           Directory.name == path.split('/')[-1]).first()
    else:
        dir_model = Directory.query.filter(Directory.parent == None and \
                                           Directory.name == path.split('/')[-1]).first()

    if dir_model is None:
        # fuck go back this directory doesn't exist as a model
        # we gotta add this shit
        print("help me: no dir for: " + path)

    print(dir_model.__dict__)
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
        print("File path: " + file_p)
        file_model = File.query.filter(File.parent == dir_model.id and \
                                       File.name == file_p).first()
        if file_model is None:
            print("help me: do file for: " + path + file_p)

        print(file_model.__dict__)

def get_dir_tree_dict():
    path = os.path.normpath("images")
    file_tree = Dict()
    for root, dirs, files in os.walk(path, topdown=True):
        path = root.split('/')
        path.pop(0)
        file_tree_fd = file_tree
        for part in path:
            file_tree_fd = file_tree_fd[part]
        file_tree_fd['.'] = files

    return file_tree


@app.route("/logout")
@auth.oidc_logout
def logout():
    return redirect(url_for('index'), 302)
