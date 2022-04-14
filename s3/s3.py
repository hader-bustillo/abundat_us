import boto3
from botocore.errorfactory import ClientError
import logging

logger = logging.getLogger(__name__)


def upload_to_aws(file_data, s3_bucket, s3_key, extra_args=None):
    s3 = boto3.client('s3')

    try:
        if extra_args:
            s3.upload_fileobj(file_data, s3_bucket, s3_key, ExtraArgs=extra_args)
        else:
            s3.upload_fileobj(file_data, s3_bucket, s3_key)
        logging.info("Uploading %s to %s was successful", repr(s3_key), repr(s3_bucket))
        return '{0}/{1}/{2}'.format(s3.meta.endpoint_url, s3_bucket, s3_key)
    except Exception as e:
        logging.exception("Uploading %s to %s had errors", repr(s3_key), repr(s3_bucket))
        return False


def download_from_aws(s3_bucket, s3_key, file_name):
    s3 = boto3.client('s3')
    logging.info("Trying to download file %s from bucket %s and saving as %s", s3_key, s3_bucket, file_name)
    try:
        with open(file_name, 'wb') as f:
            s3.download_fileobj(s3_bucket, s3_key, f)
    except:
        logging.exception("downloading %s from %s had errors", repr(s3_key), repr(s3_bucket))
        return False


def key_exists(s3_bucket, s3_key):

    s3 = boto3.client('s3')
    try:
        s3.head_object(Bucket=s3_bucket, Key=s3_key)
        return True
    except ClientError:
        return False


def list_objects(s3_bucket):
    s3 = boto3.client('s3')

    try:
        s3_obj_list = s3.list_objects(Bucket=s3_bucket)
        if 'Contents' in s3_obj_list:
            return s3_obj_list['Contents']
    except:
        logging.exception("error trying to list objects in %s", s3_bucket)

    return []


def s3_delete_all_object(s3_bucket):
    obj_list = list_objects(s3_bucket=s3_bucket)
    try:
        s3 = boto3.client('s3')
        for s3_obj in obj_list:
            s3.delete_object(Bucket=s3_bucket, Key=s3_obj['Key'])
    except:
        logging.exception("Error in deleting the object")

