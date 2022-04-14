import boto3
from datetime import datetime, timedelta
from db import dynamo
import json


def modify_type(post_result:dict):
    if 'type' in post_result:
        if 'blox' in post_result['type']:
            post_result['type'] = 'blox'
        elif 'wordpress' in post_result['type']:
            post_result['type'] = 'wordpress'
        else:
            post_result['type'] = 'file'
    else:
        post_result['type'] = 'file'


s3_bucket_name = 'posted-assets'
start_date = '2019 02 04'

date = datetime.strptime(start_date, '%Y %m %d')

end_date = '2019 11 10'
end_date_datetime = datetime.strptime(end_date, '%Y %m %d')

while date < end_date_datetime:
    cur_day_str = date.strftime('%Y %m %d')
    nex_day_str = (date + timedelta(days=1)).strftime('%Y %m %d')

    s3_client = boto3.client('s3')

    result = dynamo.dynamo_scan_table(table_name='RS_AI_POSTED_ASSETS', keys=['log_time', 'log_time'],
                             vals=[cur_day_str,nex_day_str], operators=['>=', '<'] , is_and=True)


    if result:
        if type(result) is list:
            for each_result in result:
                modify_type(each_result)

                s3_key = cur_day_str.replace(' ' , '/') + '/' + each_result['id'] + '.json'

                s3_client.put_object(Body=json.dumps(each_result),
                                     Bucket='posted-assets',
                                     Key=s3_key)
                dynamo.dynamo_put_item('RS_AI_POSTED_ASSETS', each_result)
        else:

            modify_type(result)

            s3_key = cur_day_str.replace(' ', '/') + '/' + result['id'] + '.json'

            s3_client.put_object(Body=json.dumps(result),
                                 Bucket='posted-assets',
                                 Key=s3_key)

            dynamo.dynamo_put_item('RS_AI_POSTED_ASSETS', result)

    date = date + timedelta(days=1)

    print(repr(date.isoformat()))