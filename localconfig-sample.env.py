import os

# Flask config
DEBUG=False
IP=os.environ.get('GALLERY_IP', 'localhost')
PORT=os.environ.get('GALLERY_PORT', '6969')
SERVER_NAME = os.environ.get('GALLERY_SERVER_NAME', 'localhost:6969')
SECRET_KEY = os.environ.get('GALLERY_SECRET_KEY', '')

# LDAP config
LDAP_BIND_DN=os.environ.get('GALLERY_LDAP_BIND_DN', '')
LDAP_BIND_PW=os.environ.get('GALLERY_LDAP_BIND_PW', '')

# OpenID Connect SSO config
OIDC_ISSUER = os.environ.get('GALLERY_OIDC_ISSUER', 'https://sso.csh.rit.edu/auth/realms/csh')
OIDC_CLIENT_ID = os.environ.get('GALLERY_OIDC_CLIENT_ID', 'gallery-dev')
OIDC_CLIENT_SECRET = os.environ.get('GALLERY_OIDC_CLIENT_SECRET', '')

SQLALCHEMY_DATABASE_URI = os.environ.get(
    'GALLERY_DATABASE_URI',
    'postgresql://DB_USERNAME:DB_PASSWORD@postgres.csh.rit.edu/gallery-dev')
SQLALCHEMY_TRACK_MODIFICATIONS = False

S3_URI = os.environ.get('GALLERY_S3_URI', 'https://s3.csh.rit.edu')
S3_ACCESS_ID = os.environ.get('GALLERY_S3_ACCESS_ID','')
S3_SECRET_KEY = os.environ.get('GALLERY_S3_SECRET_KEY','')
S3_BUCKET_ID = os.environ.get('GALLERY_S3_BUCKET_ID','gallery-dev')
