import jsondiff
from db import dynamo
import json


with open('configuration/input.json', 'r') as input_json:
    input = json.load(input_json)

with open('config.json') as config:
    general_config = json.load(config)['general']

for key,value in input.items():
    if 'CUSTOMER_CONFIG' in key:
        print("There are customer config changes\n")
        for item in value:
            existing_item = dynamo.dynamo_get_item(table_name=key, keys=['name'], vals=[item['name']])
            print(jsondiff.diff(existing_item,item,syntax='explicit'))
            user_inp = 'y'
#            user_inp = input("Are you satisfied with the changes? Do you wish to update ? Enter Y or N :")
            if user_inp.lower() == 'y':
                print("beginning to make updates\n")
                dynamo.dynamo_put_item(table_name=key,entry=item)

    elif 'ACTIVE_CUSTOMERS' in key:
        print("changes in active customers table\n")
        for item in value:
            try:
                existing_item = dynamo.dynamo_get_item(table_name=key, keys=['customer_name'], vals=[item['customer_name']])
            except Exception as e:
                existing_item = dynamo.dynamo_get_item(table_name=key, keys=['name'], vals=[item['name']])
            print(jsondiff.diff(existing_item,item,syntax='explicit'))
            user_inp = 'y'
            # user_inp = input("Are you satisfied with the changes? Do you wish to update ? Enter Y or N :")

            if user_inp.lower() == 'y':
                print("beginning to make updates\n")
                dynamo.dynamo_put_item(table_name=key,entry=item)


    elif 'SPORTS_CONFIG' in key:
        print("changes in sports config\n")
        for item in value:
            existing_item = dynamo.dynamo_get_item(table_name=key, keys=['key'], vals=[item['key']])
            print(jsondiff.diff(existing_item,item,syntax='explicit'))
            user_inp = 'y'
            if user_inp.lower() == 'y':
                print("beginning to make updates\n")
                dynamo.dynamo_put_item(table_name=key,entry=item)


