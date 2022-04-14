import boto3
from datetime import datetime, timedelta
import calendar

S3_MONTHLY_URL_FORMAT = 's3://posted-assets/%Y/%m/'
S3_YEARLY_URL_FORMAT = 's3://posted-assets/%Y'
S3_OUTPUT = 's3://posted-assets-athena/'
ATHENA_DB = 'posted_assets'
#Function for starting athena query

def run_query(query, database, s3_output):
    client = boto3.client('athena')
    response = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            'Database': database
            },
        ResultConfiguration={
            'OutputLocation': s3_output,
            }
        )
    print('Execution ID: ' + response['QueryExecutionId'])
    return response

def create_athena_table(database, table_name, s3_input):
    create_table = \
        """CREATE EXTERNAL TABLE IF NOT EXISTS %s.%s (
         `id` string,
         `customer_id` int,
         `customer_name` string,
         `game_id` int,
         `game_url` string,
         `home_team_id` int,
         `invoice_company` string,
         `log_time` string,
         `post_response` string,
         `post_url` string,
         `type` string 
     )
     ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
     WITH SERDEPROPERTIES (
     'serialization.format' = '1'
     ) LOCATION '%s'
     TBLPROPERTIES ('has_encrypted_data'='false');""" % (database, table_name, s3_input)

    run_query(create_table,ATHENA_DB,S3_OUTPUT)

def create_next_month_s3_bucket(new_date):
    s3_client = boto3.client('s3')

    s3_key = new_date.strftime("%Y/%m/")

    s3_client.put_object(Bucket='posted-assets',
                         Key=s3_key)


def create_view(database, view_name, table1:list, optional_query_param):

    updated_table = list(map(lambda x: """SELECT * FROM %s.%s 
                                        %s""" % (database, x, optional_query_param), table1))

    updated_table_string = """ UNION ALL """.join(updated_table)

    create_view = \
            """ CREATE OR REPLACE VIEW %s AS
            %s;""" % (view_name, updated_table_string)

    run_query(create_view,database,S3_OUTPUT)


def create_next_month_athena_table(new_date):
    if new_date.year != datetime.now().year:
        create_athena_table(database=ATHENA_DB,table_name='yearly_'+str(new_date.year),
                            s3_input=new_date.strftime(S3_YEARLY_URL_FORMAT))

    create_athena_table(database=ATHENA_DB,table_name=str(new_date.strftime("monthly_%Y_%b")).lower(),
                        s3_input=new_date.strftime(S3_MONTHLY_URL_FORMAT))


if __name__ == "__main__":
    #Execute all queries

    # based on the date, set the current year and previous year
    # set the current month view, previous month view,
    # current week view , previous week view
    # also today's view and yesterday's view

    curr_day = datetime.now()
    next_8th_day = curr_day + timedelta(days=8)

    if curr_day.month != next_8th_day.month:
        # create next month s3 bucket ,athena query a week in advance
        create_next_month_s3_bucket(next_8th_day)
        create_next_month_athena_table(new_date=next_8th_day)
    # create today and yesterday's view


    start_weekday = curr_day - timedelta(days=curr_day.weekday())
    end_weekday = start_weekday + timedelta(days=7)

    # create current weekly views
    optional_query_param = "where log_time >='%s' AND log_time <'%s'" % (start_weekday.strftime('%Y %m %d'),
                                                               end_weekday.strftime('%Y %m %d'))

    tables = str(start_weekday.strftime("monthly_%Y_%b")).lower()
    if start_weekday.month != end_weekday.month:
        tables += '$' + str(end_weekday.strftime("monthly_%Y_%b")).lower()

    tables_list = tables.split('$')

    create_view(database=ATHENA_DB,table1=tables_list,optional_query_param=optional_query_param,
                view_name='Current_Week')

    previous_week_start = start_weekday - timedelta(days=7)

    # create current weekly views
    optional_query_param = "where log_time >='%s' AND log_time <'%s'" % (previous_week_start.strftime('%Y %m %d'),
                                                               start_weekday.strftime('%Y %m %d'))

    tables = str(previous_week_start.strftime("monthly_%Y_%b")).lower()
    if start_weekday.month != previous_week_start.month:
        tables += '$' + str(start_weekday.strftime("monthly_%Y_%b")).lower()

    tables_list = tables.split('$')

    create_view(database=ATHENA_DB,table1=tables_list,optional_query_param=optional_query_param,
                view_name='Previous_Week')

    # create current month view
    tables_list = [str(curr_day.strftime("monthly_%Y_%b")).lower()]

    create_view(database=ATHENA_DB,table1=tables_list,optional_query_param="",
                view_name='Current_Month')

    #create previous month view

    previous_month_date = curr_day - timedelta(days=curr_day.day)

    tables_list = [str(previous_month_date.strftime("monthly_%Y_%b")).lower()]

    create_view(database=ATHENA_DB, table1=tables_list, optional_query_param="",
                view_name='Previous_Month')

    # create current year view

    tables_list = [curr_day.strftime("yearly_%Y")]

    create_view(database=ATHENA_DB, table1=tables_list, optional_query_param="",
                view_name='Current_Year')
    # create previous year view
    previous_year_date = curr_day.year - 1

    tables_list = [ "yearly_%d" % (previous_year_date) ]

    create_view(database=ATHENA_DB, table1=tables_list, optional_query_param="",
                view_name='Previous_Year')
