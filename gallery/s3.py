import boto
import boto.s3.connection
from boto.s3.key import Key
from datetime import timedelta

class S3():
    con = None

    def __init__(self, host, access_key=None, secret_key=None, secure=True):
        self.con = boto.connect_s3(aws_access_key_id=access_key,
                                   aws_secret_access_key=secret_key,
                                   host=host,
                                   calling_format=boto.s3.connection.OrdinaryCallingFormat())
    def put_object(self, bucket_name, key, file_handle, file_size):
        bucket = self.con.get_bucket(bucket_name)
        _key = bucket.new_key(key)
        _key.set_contents_from_file(file_handle)

    def remove_object(self, bucket_name, key):
        bucket = self.con.get_bucket(bucket_name)
        bucket.delete_key(key)

    def presigned_get_object(self, bucket_name, key, expires=timedelta(days=7)):
        bucket = self.con.get_bucket(bucket_name)
        _key = bucket.get_key(key)
        return _key.generate_url(expires.total_seconds(), query_auth=True)
