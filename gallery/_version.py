from os import environ as env

__version__ = "2.1.2"

BUILD_REFERENCE = env.get("OPENSHIFT_BUILD_REFERENCE")
COMMIT_HASH = env.get("OPENSHIFT_BUILD_COMMIT")

if BUILD_REFERENCE != "master" and COMMIT_HASH:
    __version__ = COMMIT_HASH[:7]
