import boto3
import botocore
import logging
from datetime import datetime

logger = logging.getLogger(__name__)



class s3_interactions:
    
    def get_file(self, db_name, download_name, buck_name=None):
        bn = buck_name
        BUCKET_NAME = self.get_bucket_name(bn=bn)
        s3 = boto3.resource('s3')
        try:
            s3.Bucket(BUCKET_NAME).download_file(db_name, download_name)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404": logging.info("The object does not exist.")
            else: raise
    
    
    def get_bucket_name(self, bn=None):
        if bn is not None: return bn
        else: return 'rs-scorestream-files'
    
    
    def backup_file(self,bucket, file_name, file_location):
        s3 = boto3.resource('s3')
        file = ''
        file = ''.join([file_location,file_name])
        logging.info(file)
        s3.Object(bucket, file_name).put(Body=open(file, 'rb'))
    
    
    
    def backup_all_files(self,bucket, file_names,file_location):
        '''
        ONLY RUN FROM CURRENT_DEVELOPMENT
        '''
        s3 = boto3.resource('s3')
        for name in file_names:
            self.backup_file(bucket=bucket,file_name=name,file_location=file_location)
