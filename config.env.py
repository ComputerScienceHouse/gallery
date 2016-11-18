import os

# Flask config
DEBUG=False
IP=os.environ.get('GALLERY_IP', '0.0.0.0')
PORT=os.environ.get('GALLERY_PORT', '8080')
SERVER_NAME = os.environ.get('GALLERY_SERVER_NAME', 'gallery-py.csh.rit.edu')
SECRET_KEY = os.environ.get('GALLERY_SECRET_KEY', '')

# LDAP config
LDAP_URL=os.environ.get('GALLERY_LDAP_URL', 'ldaps://ldap.csh.rit.edu:636')
LDAP_BIND_DN=os.environ.get('GALLERY_LDAP_BIND_DN', 'cn=gallery,ou=Apps,dc=csh,dc=rit,dc=edu')
LDAP_BIND_PW=os.environ.get('GALLERY_LDAP_BIND_PW', '')
LDAP_USER_OU=os.environ.get('GALLERY_LDAP_USER_OU', 'ou=Users,dc=csh,dc=rit,dc=edu')

# OpenID Connect SSO config
OIDC_ISSUER = os.environ.get('GALLERY_OIDC_ISSUER', 'https://sso.csh.rit.edu/realms/csh')
OIDC_CLIENT_CONFIG = {
    'client_id': os.environ.get('GALLERY_OIDC_CLIENT_ID', 'gallery'),
    'client_secret': os.environ.get('GALLERY_OIDC_CLIENT_SECRET', ''),
    'post_logout_redirect_uris': [os.environ.get('GALLERY_OIDC_LOGOUT_REDIRECT_URI',
                                                 'https://gallery-py.csh.rit.edu/logout')]
}
SQLALCHEMY_DATABASE_URI = os.environ.get(
    'GALLERY_DATABASE_URI',
    'sqlite:///{}'.format(os.path.join(os.getcwd(), 'data.db')))
SQLALCHEMY_TRACK_MODIFICATIONS = False
