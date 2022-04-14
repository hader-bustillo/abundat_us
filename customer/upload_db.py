from db import dynamo
import json
import decimal

with open('config.json') as config_file:
    configuration = json.load(config_file, parse_float=decimal.Decimal)['scheduler']

for each_item in configuration['customers']:

    print(each_item)
    dynamo.dynamo_put_item('RS_ACTIVE_CUSTOMERS_TEST', each_item)
