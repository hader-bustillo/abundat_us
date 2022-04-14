from db import dynamo
import json

table_name = "RS_ACTIVE_CUSTOMERS_TEST"
key = "customer_name"
value = "Richland Source Ohio"
scan = False

if scan:
    with open('configuration/tmp.json', 'w') as input_json:

        items = dynamo.dynamo_db_scan(table_name=table_name)

        item = {table_name: items}
        json.dump(item, input_json, indent=4)
else:
    with open('configuration/tmp.json', 'w') as input_json:

        existing_item = dynamo.dynamo_get_item(table_name=table_name, keys=[key], vals=[value])
        json.dump(existing_item, input_json, indent=4)




