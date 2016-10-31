import os

from flask import Flask
from flask import redirect
from flask import url_for
from flask import session

from flask_pyoidc.flask_pyoidc import OIDCAuthentication

import requests

app = Flask(__name__)

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

@app.route("/logout")
@auth.oidc_logout
def logout():
    return redirect(url_for('index'), 302)
