import os
import shutil
from datetime import timedelta
from typing import IO

import boto3
from botocore.client import Config
import flask
from flask import abort, send_from_directory, url_for
from itsdangerous import (
    URLSafeTimedSerializer
)


class FileStorage(object):
    """
    FileStorage represents the interface for interacting with some kind of
    backing storage system. This system is used to store the actual image and
    thumbnail data persistantly.
    """

    def put(self, key: str, handle: IO[bytes]):
        """
        put is used to stream data from a local file descriptor into the backing
        storage implementation.
        """
        pass

    def remove(self, key: str):
        """
        delete will remove a given file from the backing storage implementation
        """
        pass

    def get_link(self, key: str) -> str:
        """
        get_link is used to return a publically facing link to a file in the
        backing storage system.
        """
        pass


class LocalStorage(FileStorage):
    """
    LocalStorage uses a local filesystem path as the basis for storing and
    serving photos and thumbnails. We generate temp links using the
    itsdangerous library.
    """
    def __init__(self, app: flask.Flask):
        self._serializer = URLSafeTimedSerializer(
            secret_key=app.config["SECRET_KEY"],
        )
        self._base_dir = app.config["LOCAL_STORAGE_PATH"]
        self._link_expiration = timedelta(days=7)
        app.route("/public/<token>")(self._temp_link_handler)

    def _temp_link_handler(self, token: str):
        try:
            payload = self._serializer.loads(token, max_age=int(self._link_expiration.total_seconds()))
        except Exception:
            # NOTE(rossdylan): We are being broad here because in any case that
            # this fails we just want to abort. This is because the token has
            # expired, been tampered with, or is just invalid. Maybe we can
            # log each case differently later...
            abort(404)

        if "key" not in payload:
            abort(404)

        # NOTE(rossdylan): We are relying on flask's protections to avoid
        # traversals or any other weirdness here. /should/ be fine since we
        # sign and verify the file path anyway
        return send_from_directory(self._base_dir, payload["key"])

    def put(self, key: str, handle: IO[bytes]):
        local_path = os.path.join(self._base_dir, key)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'wb+') as f:
            shutil.copyfileobj(handle, f)

    def remove(self, key: str):
        local_path = os.path.join(self._base_dir, key)
        os.remove(local_path)

    def get_link(self, key: str):
        return url_for("_temp_link_handler", token=self._serializer.dumps({"key": key}))


class S3Storage(FileStorage):
    """
    S3Storage is the main storage implementation that uses an s3-like system
    to store thumbnails and photos. Links are generated using the presigned
    url function of S3.
    """
    def __init__(self, app: flask.Flask):
        self._client = boto3.client(
            's3',
            aws_access_key_id=app.config['S3_ACCESS_ID'],
            aws_secret_access_key=app.config['S3_SECRET_KEY'],
            endpoint_url=app.config['S3_URI'],
            config=Config(signature_version='s3v4'),
        )
        self._bucket = app.config['S3_BUCKET_ID']
        self._link_expiration = timedelta(minutes=5)

    def put(self, key: str, handle: IO[bytes]):
        self._client.upload_fileobj(handle, self._bucket, key)

    def remove(self, key: str):
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def get_link(self, key: str) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._bucket,
                "Key": key,
            },
            ExpiresIn=self._link_expiration.total_seconds(),
        )
