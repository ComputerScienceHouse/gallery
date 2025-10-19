from os import environ as env
from setuptools.config.setupcfg import read_configuration

config = read_configuration('setup.cfg')
__version__ = config["metadata"]["version"]

BUILD_REFERENCE = env.get("OPENSHIFT_BUILD_REFERENCE")
COMMIT_HASH = env.get("OPENSHIFT_BUILD_COMMIT")

if BUILD_REFERENCE != "master" and COMMIT_HASH:
    __version__ = COMMIT_HASH[:7]
