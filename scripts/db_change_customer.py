from db import dynamo
import boto3

city_list = ["Princeton,IL", 
"Manilus,IL", 
"Spring Valley, IL"]

long_lat = [[41.359916,-89.474218]]

customer_name = 'BrentwoodHomepage'
invoice_company = 'Homepagemedia'
#test = dynamo.dynamo_db_scan(table_name='RS_ACTIVE_CUSTOMERS_TEST')
test = dynamo.dynamo_get_item(table_name='RS_CUSTOMER_CONFIG_DEV', keys=['name'],vals=[customer_name])

publishing_system = test['publishing_system']
coverage = test['coverage']
location = test['location']

html_string = "<p>This sports coverage is possible through the generous support of our members. To become a member for as little as $5 per month, <a href=\"https://www.getrevue.co/profile/whatsupnewp/members \">follow this link.</a></p> <p> </p> <p> </p>You're reading a news brief powered by <a href=\"https://whatsupnewp.com\">WhatsUpNewp</a> and <a href=\"https://scorestream.com/gettheapp\">ScoreStream</a>, the world leader in fan-driven sports results and conversation. To see more game results from your favorite team, download the ScoreStream app and join nearly a million users nationwide who share the scores of their favorite teams with one another in real-time."

text_string = "\nThis sports coverage is possible through the generous support of our members. To become a member for as little as $5 per month, head over to https://www.getrevue.co/profile/whatsupnewp/members.\n\nYou're reading a news brief powered by WhatsUpNewp and ScoreStream, the world leader in fan-driven sports results and conversation. To see more game results from your favorite team, download the ScoreStream app and join nearly a million users nationwide who share the scores of their favorite teams with one another in real-time."

html_string1 = "<p>This sports coverage is possible through the generous support of our members. To become a member for as little as $5 per month, <a href=\"https://www.getrevue.co/profile/whatsupnewp/members \">follow this link.</a></p> <p> </p> <p> </p>You're reading a news brief powered by <a href=\"https://whatsrhodeisland.com\">WhatsUpRhodeIsland</a> and <a href=\"https://scorestream.com/gettheapp\">ScoreStream</a>, the world leader in fan-driven sports results and conversation. To see more game results from your favorite team, download the ScoreStream app and join nearly a million users nationwide who share the scores of their favorite teams with one another in real-time."

text_string1 = "\nThis sports coverage is possible through the generous support of our members. To become a member for as little as $5 per month, head over to https://www.getrevue.co/profile/whatsupnewp/members.\n\nYou're reading a news brief powered by WhatsUpRhodeIsland and ScoreStream, the world leader in fan-driven sports results and conversation. To see more game results from your favorite team, download the ScoreStream app and join nearly a million users nationwide who share the scores of their favorite teams with one another in real-time."
dev = dynamo.dynamo_db_scan(table_name='RS_CUSTOMER_CONFIG')

dynamodb = boto3.resource('dynamodb')
table1 = dynamodb.Table('RS_CUSTOMER_CONFIG')

#table1.delete_item(Key={'name': str(customer_name+'backup')})
for item in dev:
    if 'invoice_company' in item and item['invoice_company'] == invoice_company:
        item['coverage'] = coverage
        item['location'] = location
        table1.delete_item(Key={'name': item['name']})
        dynamo.dynamo_put_item(table_name='RS_CUSTOMER_CONFIG', entry=item)



# table1.delete_item(Key={'name': customer_name})
#
# prod['name'] = customer_name
#
# dynamo.dynamo_put_item(table_name='RS_CUSTOMER_CONFIG', entry=prod)
