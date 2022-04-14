import pytest
import json
import responses
import boto3
from moto import mock_dynamodb2, mock_s3
from db.dynamo import replaceEmptyString, removeEmptyString
from decimal import Decimal
from scorestream import ss_integration
from db import dynamo
from s3 import s3
from copy import deepcopy
import ai_article_handler as aah
import logging
from utils import utils
from customer import customer_config
import sys
from datetime import datetime
import os
from publisher import publish_handler
import config


logging.basicConfig(level=getattr(logging, "INFO"),
                    format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
                    handlers=[
                        logging.StreamHandler(sys.stdout)
                    ])


@pytest.fixture(scope='module')
def create_s3():
    with mock_s3():
        s3 = boto3.client('s3')
        general_config = get_general_config()
        s3_bucket = general_config['article_s3_bucket']
        output = s3.create_bucket(Bucket=s3_bucket)


@pytest.fixture(scope='module')
def dynamodb_tables():
    with mock_dynamodb2():
        with open('tests/data/general_config.json') as configuration:
            general_config = json.load(configuration)
        dynamodb = boto3.resource('dynamodb')

        game_table = dynamodb.create_table(
            TableName=general_config['games_table'],
            KeySchema=[
                {
                    'AttributeName': 'gameId',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'homeTeamId',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'gameId',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'homeTeamId',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'startDateTime',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'sportName',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'homeSquadId',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'awayTeamId',
                    'AttributeType': 'N'
                }

            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': general_config['games_sports_start_time_index'],
                    'KeySchema': [
                        {
                            'AttributeName': 'sportName',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'startDateTime',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'INCLUDE',
                        'NonKeyAttributes': [
                            'homeSquadId',
                            'awayTeamId'
                        ]
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 10,
                        'WriteCapacityUnits': 10
                    }
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        unique_table = dynamodb.create_table(
            TableName='CONTENT_FOR_UNIQUE_TAG',
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }

            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        team_table = dynamodb.create_table(
            TableName=general_config['teams_table'],
            KeySchema=[
                {
                    'AttributeName': 'teamId',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'teamId',
                    'AttributeType': 'N'
                }

            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        squad_table = dynamodb.create_table(
            TableName=general_config['squads_table'],
            KeySchema=[
                {
                    'AttributeName': 'squadId',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'sqaudId',
                    'AttributeType': 'N'
                }

            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        colors_table = dynamodb.create_table(
            TableName='RS_AI_SS_COLORS',
            KeySchema=[
                {
                    'AttributeName': 'colorId',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'colorId',
                    'AttributeType': 'N'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        team_pics_table = dynamodb.create_table(
            TableName='RS_AI_SS_TEAM_PICS',
            KeySchema=[
                {
                    'AttributeName': 'teamPictureId',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'teamPictureId',
                    'AttributeType': 'N'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        errors_table = dynamodb.create_table(
            TableName='RS_AI_SS_ERRORS',
            KeySchema=[
                {
                    'AttributeName': 'pk',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'pk',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        customer_config_table = dynamodb.create_table(
            TableName=general_config['customer_config_table'],
            KeySchema=[
                {
                    'AttributeName': 'name',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'name',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        with open('tests/data/customer_config.json') as config_file:
            configuration = json.load(config_file, parse_float=Decimal)
            configuration = removeEmptyString(configuration)
        customer_config_table.put_item(Item=configuration)

        sports_config_table = dynamodb.create_table(
            TableName=general_config['sports_config'],
            KeySchema=[
                {
                    'AttributeName': 'key',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'key',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        with open('tests/data/sports_config.json') as config_file:
            configuration = json.load(config_file, parse_float=Decimal)
        for item in configuration['sports']:
            item = removeEmptyString(item)
            sports_config_table.put_item(Item=item)

        active_customers_table_test = dynamodb.create_table(
            TableName=general_config['active_customers'],
            KeySchema=[
                {
                    'AttributeName': 'customer_name',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'key',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        posted_assets = dynamodb.create_table(
            TableName=general_config['posted_assets_table'],
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'game_start_time',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'game_start_time',
                    'AttributeType': 'S'
                },

            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        posted_assets_alt = dynamodb.create_table(
            TableName=general_config['posted_assets_table_alt'],
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'game_start_time',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'game_start_time',
                    'AttributeType': 'S'
                },

            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        rs_senior_spotlight = dynamodb.create_table(
            TableName=general_config['senior_spot_light'],
            KeySchema=[
                {
                    'AttributeName': 'dateAdded',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'dateAdded',
                    'AttributeType': 'S'
                }

            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        rs_processed_senior_spotlight = dynamodb.create_table(
            TableName=general_config['processed_senior_spot_light'],
            KeySchema=[
                {
                    'AttributeName': 'dateAdded',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'dateAdded',
                    'AttributeType': 'S'
                }

            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        article_content_table = dynamodb.create_table(
            TableName=general_config['article_content_table'],
            KeySchema=[
                {
                    'AttributeName': 'content_type',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'content_type',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        with open('tests/data/article_content.json') as config_file:
            article_content = json.load(config_file, parse_float=Decimal)
        for key, value in article_content.items():
            item = value
            item = removeEmptyString(item)
            article_content_table.put_item(Item=item)


        general_config_table = dynamodb.create_table(
            TableName=config.GENERAL_CONFIG_TABLE,
            KeySchema=[
                {
                    'AttributeName': 'key',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'key',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }

        )

        general_config_table.put_item(Item=general_config)

        yield


@pytest.fixture
def games_teams_squad_list():
    with open('tests/data/game_data.json') as collections:
        collection_list = json.load(collections, parse_float=Decimal)
        yield collection_list['game_list'], collection_list['team_list'], collection_list['squad_list']


def get_general_config():
    general_config = dynamo.dynamo_get_item(table_name=config.GENERAL_CONFIG_TABLE, keys=['key'],
                                            vals=["ledeai-circleci-testserver"])
    return general_config


@pytest.fixture
def loaded_dynamo(dynamodb_tables):
    with open('tests/data/game_data.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)
        for item in configuration['game_list']:
            dynamo.dynamo_put_item(table_name='RS_AI_SS_GAMES', entry=process_ss_game_data(item))
        for item in configuration['team_list']:
            dynamo.dynamo_put_item(table_name='RS_AI_SS_TEAMS', entry=item)
        for item in configuration['squad_list']:
            dynamo.dynamo_put_item(table_name='RS_AI_SS_SQUADS', entry=item)
    yield


@pytest.fixture
def response_samples():
    with responses.RequestsMock() as rsps:
        yield rsps


def process_ss_game_data(ss_game):
    logging.info("Processing_ss_game_data for game %d\n", ss_game['gameId'])
    away_final_score = 9999
    home_final_score = 9999
    confidence_grade = 90
    stoppage_id = 9999
    stoppage_message = 'NONE_TEXT'

    last_score = ss_game['lastScore']
    if 'awayTeamScore' in last_score: away_final_score = last_score['awayTeamScore']
    if 'homeTeamScore' in last_score: home_final_score = last_score['homeTeamScore']
    if 'confidenceGrade' in last_score: confidence_grade = last_score['confidenceGrade']
    if 'stoppageStatusId' in last_score: stoppage_id = last_score['stoppageStatusId']
    if 'stoppageMessage' in last_score: stoppage_message = last_score['stoppageMessage']

    lat_long = convert_vals_to_str(ss_game)

    date_arr = filter_text(text=ss_game['startDateTime'], num_chars=10, from_left=True, separator='-')
    game_year = int(date_arr[0])
    game_month = int(date_arr[1])
    game_day = int(date_arr[2])

    del_keys = []
    del_keys = del_keys + ['hideLevel', 'useGameClock', 'rankBonus',
                                     'scheduleCategoryId', 'branchedUsers', 'longitude', 'latitude']

    del_unnecessary(del_keys, ss_game)

    add_values_to_dict(keys=['awayTeamScore', 'homeTeamScore', 'confidenceGrade', 'stoppageStatusId',
                                  'stoppageMessage', 'gameYear', 'gameMonth', 'gameDay', 'longitude', 'latitude'],
                            vals=[away_final_score, home_final_score, confidence_grade, stoppage_id,
                                  stoppage_message,
                                  int(game_year), int(game_month), int(game_day), lat_long[0], lat_long[1]],
                            coll=ss_game, func_name='process_ss_game_data')

    logging.info("Completed  Processing_ss_game_data for game %d\n", ss_game['gameId'])

    return ss_game

def del_unnecessary(attributes, coll):
    '''
    attributes is [str] with the keys to delete. coll is the dict.
    '''
    for item in attributes:
        if item in coll:
            del coll[item]
    return coll

def add_values_to_dict(keys, vals, coll, func_name):
    '''
    keys are a [str], vals are [vars], coll is the dict they're being added to
    '''
    for i in range(len(keys)):
        coll[keys[i]] = vals[i]
    return coll

def filter_text(text, num_chars, from_left, separator=None):
    t = ''
    if from_left is True:
        t = text[0:num_chars]
    else:
        t = text[-num_chars:]

    if separator is not None:
        return t.split('-')
    else:
        return t

def convert_vals_to_str(entry):
    if 'aspectRatio' in entry:
        return (str(entry['aspectRatio']), 'NONE_TEXT')
    if 'longitude' not in entry:
        return (0, 0)
    else:
        long = str(entry['longitude'])
        lat = str(entry['latitude'])
        return (long, lat)

class Message:
    def __init__(self,message):
        self.body = message
        self.headers = 'Test'


def test_scorestream_call_and_database_check(dynamodb_tables):
    logging.info("Test for testing scroestream braodcast call")
    api_key = 'd572dff0-1e62-4f8d-962b-589bed0d6e24'

    location = {'latitude': 41.738379, 'longitude': -80.817047}

    parameters = {
        'location': location,
        'apiKey': api_key,
        'count': 100,
        'afterDateTime': "2019-09-04 00:00:00",
        'beforeDateTime': "2019-09-04 23:00:00",
    }
    responses.add_passthru('https://')
    responses.add_passthru('http://')
    result = ss_integration.get_result_and_upload(params=parameters,method='recommended.broadcast.games.search')
    logging.info("received the response from scorestream - %s", repr(result))
    assert result != []
    logging.info("Received good response from scorestream for braodcast call")


def test_customer_config_validation_for_fields(dynamodb_tables):

    general_config = get_general_config()
    customer_test = customer_config.CustomerConfig(customer_name='Test', general_config=general_config)
    assert customer_test.name == 'Test'
    assert customer_test.test_system is True
    assert customer_test.editor_email == 'jothi@abundat.com'
    assert customer_test.headline == "this is a test"
    assert customer_test.location == [[41.738379, -80.817047]]
    assert customer_test.coverage == [
                   {
                     "sport": "all",
                     "definition": "state",
                     "id_lists" : ["OH"],
                     "sports_level": [1010, 1040]
                   }
    ]
    assert customer_test.trailer_boiler_plate == {
        "text": "\nIf you would like to join in the action,download the Scorestream app today.\nThis sports coverage is possible through the generous support of our members. To become a member for as little as $5 per month, follow this link.",
        "html": "<p><a href=\"https://scorestream.com/gettheapp\">If you would like to join in the action, download the Scorestream app today.</a></p><p>This sports coverage is possible through the generous support of our members. To become a member for as little as $5 per month, <a href=\"https://www.sourcemembers.com/\">follow this link.</a></p>"
    }
    assert customer_test.auto_publish == False

    sports_list = ['football', 'soccer', 'baseball', 'softball', 'basketball', 'hockey', 'lacrosse', 'volleyball']

    for each_sport in customer_test.sports_interested:
        assert each_sport in sports_list


def test_customer_config_validation_for_include_cities_for_sport(dynamodb_tables, games_teams_squad_list):
    dynamodb = boto3.resource('dynamodb')

    general_config = get_general_config()

    games_list, teams_list, squad_list = games_teams_squad_list
    customer_config_table_name = general_config['customer_config_table']
    table1 = dynamodb.Table(customer_config_table_name)

    table1.delete_item(Key={'name': 'Test'})

    with open('tests/data/customer_config_include_cities_sport.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

        dynamo.dynamo_put_item(table_name=customer_config_table_name,entry=configuration)

        customer_test = customer_config.CustomerConfig(customer_name='Test', general_config=general_config)
        customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)

        assert customer_test.coverage_team_list == {'all': {'teams': [1,2,3,4,5,6,7], 'exclude_teams':[]},
                                                    'soccer': {'teams':[1,2,5], 'exclude_teams':[]}}


def test_customer_config_validation_for_include_cities_for_all(dynamodb_tables, games_teams_squad_list):
    dynamodb = boto3.resource('dynamodb')

    games_list, teams_list, squad_list = games_teams_squad_list

    general_config = get_general_config()

    customer_config_table_name = general_config['customer_config_table']
    table1 = dynamodb.Table(customer_config_table_name)

    table1.delete_item(Key={'name': 'Test'})

    with open('tests/data/customer_config_include_cities_all.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

        dynamo.dynamo_put_item(table_name=customer_config_table_name, entry=configuration)

        customer_test = customer_config.CustomerConfig(customer_name='Test', general_config=general_config)
        customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)

        # assert all the team id's

        assert customer_test.coverage_team_list == {'all': {'exclude_teams': [], 'teams': [1, 2, 5]}}


def test_customer_config_validation_for_exclude_cities_for_sport(dynamodb_tables, games_teams_squad_list):
    dynamodb = boto3.resource('dynamodb')

    games_list, teams_list, squad_list = games_teams_squad_list
    general_config = get_general_config()
    customer_config_table_name = general_config['customer_config_table']
    table1 = dynamodb.Table(customer_config_table_name)

    table1.delete_item(Key={'name': 'Test'})

    with open('tests/data/customer_config_exclude_cities_sport.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

        dynamo.dynamo_put_item(table_name=customer_config_table_name, entry=configuration)

        customer_test = customer_config.CustomerConfig(customer_name='Test', general_config=general_config)

        customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)

        # assert all the team id's

        assert customer_test.coverage_team_list == {'all': {'exclude_teams': [], 'teams': [1, 2, 3, 4, 5, 6, 7]},
                                                    'football': {'exclude_teams': [1, 2, 5], 'teams': [3, 4, 6, 7]}}


def test_customer_config_validation_for_exclude_cities_for_all(dynamodb_tables, games_teams_squad_list):
    dynamodb = boto3.resource('dynamodb')

    games_list, teams_list, squad_list = games_teams_squad_list

    general_config = get_general_config()

    customer_config_table_name = general_config['customer_config_table']
    table1 = dynamodb.Table(customer_config_table_name)

    table1.delete_item(Key={'name': 'Test'})

    with open('tests/data/customer_config_exclude_cities_all.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

        dynamo.dynamo_put_item(table_name=customer_config_table_name, entry=configuration)

        customer_test = customer_config.CustomerConfig(customer_name='Test', general_config=general_config)

        customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)

        # assert all the team id's

        assert customer_test.coverage_team_list == {'all': {'exclude_teams': [1, 2, 5], 'teams': [3, 4, 6, 7]}}


def test_customer_config_validation_for_team_id_for_sport(dynamodb_tables, games_teams_squad_list):
    dynamodb = boto3.resource('dynamodb')

    games_list, teams_list, squad_list = games_teams_squad_list

    general_config = get_general_config()

    customer_config_table_name = general_config['customer_config_table']
    table1 = dynamodb.Table(customer_config_table_name)

    table1.delete_item(Key={'name': 'Test'})

    with open('tests/data/customer_config_team_ids_sport.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

        dynamo.dynamo_put_item(table_name=customer_config_table_name, entry=configuration)

        customer_test = customer_config.CustomerConfig(customer_name='Test', general_config=general_config)

        customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)

        # assert all the team id's

        assert customer_test.coverage_team_list == {'all': {'exclude_teams': [], 'teams': [1, 2, 3, 4, 5, 6, 7]},
                                                    'soccer': {'exclude_teams': [], 'teams': [1]}}


def test_customer_config_validation_for_team_id_for_all(dynamodb_tables, games_teams_squad_list):
    dynamodb = boto3.resource('dynamodb')

    games_list, teams_list, squad_list = games_teams_squad_list

    general_config = get_general_config()

    customer_config_table_name = general_config['customer_config_table']
    table1 = dynamodb.Table(customer_config_table_name)

    table1.delete_item(Key={'name': 'Test'})

    with open('tests/data/customer_config_team_ids_all.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

        dynamo.dynamo_put_item(table_name=customer_config_table_name, entry=configuration)

        customer_test = customer_config.CustomerConfig(customer_name='Test', general_config=general_config)

        customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)

        # assert all the team id's

        assert customer_test.coverage_team_list == {'all': {'exclude_teams': [], 'teams': [1]}}


def test_customer_config_validation_for_sqaud_id_for_sport(dynamodb_tables, games_teams_squad_list):
    dynamodb = boto3.resource('dynamodb')

    games_list, teams_list, squad_list = games_teams_squad_list

    general_config = get_general_config()

    customer_config_table_name = general_config['customer_config_table']
    table1 = dynamodb.Table(customer_config_table_name)

    table1.delete_item(Key={'name': 'Test'})

    with open('tests/data/customer_config_squad_specific_sport.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

        dynamo.dynamo_put_item(table_name=customer_config_table_name, entry=configuration)

        customer_test = customer_config.CustomerConfig(customer_name='Test', general_config=general_config)

        customer_test.coverage_squad_list = customer_test.get_list_of_squads_by_sport()

        # assert all the team id's

        assert customer_test.coverage_squad_list == {'all': [1010,1040],
                                                     'soccer': [1040]}


def test_customer_config_validation_for_sqaud_id_for_all(dynamodb_tables, games_teams_squad_list):
    dynamodb = boto3.resource('dynamodb')

    games_list, teams_list, squad_list = games_teams_squad_list

    general_config = get_general_config()

    customer_config_table_name = general_config['customer_config_table']
    table1 = dynamodb.Table(customer_config_table_name)

    table1.delete_item(Key={'name': 'Test'})

    with open('tests/data/customer_config_squad_specific_all.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

        dynamo.dynamo_put_item(table_name=customer_config_table_name, entry=configuration)

        customer_test = customer_config.CustomerConfig(customer_name='Test', general_config=general_config)
        customer_test.coverage_squad_list = customer_test.get_list_of_squads_by_sport()
        # assert all the team id's

        assert customer_test.coverage_squad_list == {'all': [1040]}


def cleanup_s3():
    general_config = get_general_config()

    s3_bucket = general_config['article_s3_bucket']
    s3.s3_delete_all_object(s3_bucket=s3_bucket)


def assert_object_exists(customer_name, run_time_id, current_date_time):

    general_config = get_general_config()

    s3_bucket = general_config['article_s3_bucket']
    txt_s3_key = os.path.join(customer_name, current_date_time.strftime("%Y-%m-%d"), current_date_time.strftime("%H-%M"),
                              run_time_id + '.txt')
    html_s3_key = os.path.join(customer_name, current_date_time.strftime("%Y-%m-%d"), current_date_time.strftime("%H-%M"),
                               run_time_id + '.html')

    assert s3.key_exists(s3_bucket=s3_bucket, s3_key=txt_s3_key)
    assert s3.key_exists(s3_bucket=s3_bucket, s3_key=html_s3_key)

    obj_list = s3.list_objects(s3_bucket=s3_bucket)

    for file_obj in obj_list:
        assert file_obj['Size'] > 0

    return True


def test_games_article_code_10(response_samples, dynamodb_tables, create_s3, monkeypatch):
    dynamodb = boto3.resource('dynamodb')

    general_config = get_general_config()

    customer_config_table_name = general_config['customer_config_table']

    table1 = dynamodb.Table(customer_config_table_name)

    table1.delete_item(Key={'name': 'Test'})

    with open('tests/data/customer_config.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)
        configuration = removeEmptyString(configuration)

    dynamo.dynamo_put_item(table_name=customer_config_table_name, entry=configuration)

    with open('tests/data/article_code_10_football.json', 'r') as scorestream_data:

        response_samples.add(responses.GET, "http://scorestream.com/api",
                             json=json.load(scorestream_data), status=200)

        # Because its mocked data, these dates are never used in the scorestream call

        today_date_time = datetime.strptime("2018-01-04 17:00:00", "%Y-%m-%d %H:%M:%S")

        monkeypatch.setattr('utils.utils.get_random_int', lambda x: 1)
        monkeypatch.setattr('utils.utils.get_scheduler_offset', lambda general_config: 60)

        current_date_time = datetime.now()
        run_time_id = "test_article"
        aah.process_article_request(customer_name="Test", fixed_date_time=today_date_time,
                                    game_range_days=0, delete_files=False,
                                    current_date_time=current_date_time,
                                    run_time_id=run_time_id, general_config=general_config)

        assert_object_exists(customer_name="Test",
                             run_time_id=run_time_id,
                             current_date_time=current_date_time)

        cleanup_s3()

        with open('output/test_ARTICLES_11_5_2017.txt', 'r') as out_file:
            content = out_file.read()
            print(content)
            assert True if 'ARTICLE CODE: 10' in content else False
            assert True if 'SPORT: football' in content else False
            assert True if 'GAMEID:\n999992' in content else False
            assert False if '[[' in content else True
        os.remove('output/test_ARTICLES_11_5_2017.txt')


def test_games_article_code_20(response_samples, dynamodb_tables, create_s3, monkeypatch):

    general_config = get_general_config()

    with open('tests/data/article_code_20_football.json', 'r') as scorestream_data:

        response_samples.add(responses.GET, "http://scorestream.com/api",
                             json=json.load(scorestream_data), status=200)

        # Because its mocked data, these dates are never used in the scorestream call

        today_date_time = datetime.strptime("2018-01-05 17:00:00", "%Y-%m-%d %H:%M:%S")

        monkeypatch.setattr('utils.utils.get_random_int', lambda x: 1)
        monkeypatch.setattr('utils.utils.get_scheduler_offset', lambda general_config: 60)

        current_date_time = datetime.now()
        run_time_id = "test_article"
        aah.process_article_request(customer_name="Test", fixed_date_time=today_date_time,
                                    game_range_days=0, delete_files=False,
                                    current_date_time=current_date_time,
                                    run_time_id=run_time_id, general_config = general_config)

        assert_object_exists(customer_name="Test",
                             run_time_id=run_time_id,
                             current_date_time=current_date_time)
        cleanup_s3()

        with open('output/test_ARTICLES_11_6_2017.txt', 'r') as out_file:
            content = out_file.read()
            print(content)
            assert True if 'ARTICLE CODE: 20' in content else False
            assert True if 'SPORT: football' in content else False
            assert True if 'GAMEID:\n999993' in content else False
            assert False if '[[' in content else True
        os.remove('output/test_ARTICLES_11_6_2017.txt')


def test_games_article_code_30(response_samples, dynamodb_tables, monkeypatch):

    with open('tests/data/article_code_30_football.json', 'r') as scorestream_data:

        response_samples.add(responses.GET, "http://scorestream.com/api",
                             json=json.load(scorestream_data), status=200)

        # Because its mocked data, these dates are never used in the scorestream call

        today_date_time = datetime.strptime("2018-01-06 17:00:00", "%Y-%m-%d %H:%M:%S")

        monkeypatch.setattr('utils.utils.get_random_int', lambda x: 1)
        monkeypatch.setattr('utils.utils.get_scheduler_offset',  lambda general_config: 60)

        current_date_time = datetime.now()
        run_time_id = "test_article"
        aah.process_article_request(customer_name="Test", fixed_date_time=today_date_time,
                                    game_range_days=0, delete_files=False,
                                    current_date_time=current_date_time,
                                    run_time_id=run_time_id,  general_config = get_general_config())

        assert_object_exists(customer_name="Test",
                             run_time_id=run_time_id,
                             current_date_time=current_date_time)
        cleanup_s3()

        with open('output/test_ARTICLES_11_7_2017.txt', 'r') as out_file:
            content = out_file.read()
            print(content)
            assert True if 'ARTICLE CODE: 30' in content else False
            assert True if 'SPORT: football' in content else False
            assert True if 'GAMEID:\n999994' in content else False
            assert False if '[[' in content else True
        os.remove('output/test_ARTICLES_11_7_2017.txt')


def test_games_article_code_40(response_samples, dynamodb_tables,monkeypatch):

    with open('tests/data/article_code_40_football.json', 'r') as scorestream_data:

        response_samples.add(responses.GET, "http://scorestream.com/api",
                             json=json.load(scorestream_data), status=200)

        # Because its mocked data, these dates are never used in the scorestream call

        today_date_time = datetime.strptime("2018-01-03 17:00:00", "%Y-%m-%d %H:%M:%S")
        monkeypatch.setattr('utils.utils.get_scheduler_offset',  lambda general_config: 60)

        current_date_time = datetime.now()
        run_time_id = "test_article"
        aah.process_article_request(customer_name="Test", fixed_date_time=today_date_time,
                                    game_range_days=0, delete_files=False,
                                    current_date_time=current_date_time,
                                    run_time_id=run_time_id, general_config=get_general_config())

        assert_object_exists(customer_name="Test",
                             run_time_id=run_time_id,
                             current_date_time=current_date_time)
        cleanup_s3()

        with open('output/test_ARTICLES_11_4_2017.txt', 'r') as out_file:
            content = out_file.read()
            print(content)
            assert True if 'ARTICLE CODE: 40' in content else False
            assert True if 'SPORT: football' in content else False
            assert True if 'GAMEID:\n999991' in content else False
            assert False if '[[' in content else True
        os.remove('output/test_ARTICLES_11_4_2017.txt')


def test_games_article_code_50(response_samples, dynamodb_tables, monkeypatch):

    with open('tests/data/article_code_50_football.json', 'r') as scorestream_data:

        response_samples.add(responses.GET, "http://scorestream.com/api",
                             json=json.load(scorestream_data), status=200)

        # Because its mocked data, these dates are never used in the scorestream call

        today_date_time = datetime.strptime("2018-01-07 17:00:00", "%Y-%m-%d %H:%M:%S")
        monkeypatch.setattr('utils.utils.get_scheduler_offset',  lambda general_config: 60)

        current_date_time = datetime.now()
        run_time_id = "test_article"
        aah.process_article_request(customer_name="Test", fixed_date_time=today_date_time,
                                    game_range_days=0, delete_files=False,
                                    current_date_time=current_date_time,
                                    run_time_id=run_time_id,general_config=get_general_config())

        assert_object_exists(customer_name="Test",
                             run_time_id=run_time_id,
                             current_date_time=current_date_time)
        cleanup_s3()

        with open('output/test_ARTICLES_11_8_2017.txt', 'r') as out_file:
            content = out_file.read()
            print(content)
            assert True if 'ARTICLE CODE: 50' in content else False
            assert True if 'SPORT: football' in content else False
            assert True if 'GAMEID:\n999995' in content else False
            assert False if '[[' in content else True
        os.remove('output/test_ARTICLES_11_8_2017.txt')


def test_games_article_code_60(response_samples, dynamodb_tables, monkeypatch):

    with open('tests/data/article_code_60_football.json', 'r') as scorestream_data:

        response_samples.add(responses.GET, "http://scorestream.com/api",
                             json=json.load(scorestream_data), status=200)

        # Because its mocked data, these dates are never used in the scorestream call

        today_date_time = datetime.strptime("2018-01-08 17:00:00", "%Y-%m-%d %H:%M:%S")
        monkeypatch.setattr('utils.utils.get_scheduler_offset',  lambda general_config: 60)

        current_date_time = datetime.now()
        run_time_id = "test_article"
        aah.process_article_request(customer_name="Test", fixed_date_time=today_date_time,
                                    game_range_days=0, delete_files=False,
                                    current_date_time=current_date_time,
                                    run_time_id=run_time_id,general_config=get_general_config())

        assert_object_exists(customer_name="Test",
                             run_time_id=run_time_id,
                             current_date_time=current_date_time)
        cleanup_s3()

        with open('output/test_ARTICLES_11_9_2017.txt', 'r') as out_file:
            content = out_file.read()
            print(content)
            assert True if 'ARTICLE CODE: 60' in content else False
            assert True if 'SPORT: football' in content else False
            assert True if 'GAMEID:\n999996' in content else False
            assert False if '[[' in content else True
        os.remove('output/test_ARTICLES_11_9_2017.txt')


def test_games_article_code_70(response_samples, dynamodb_tables, monkeypatch):

    with open('tests/data/article_code_70_football.json', 'r') as scorestream_data:

        response_samples.add(responses.GET, "http://scorestream.com/api",
                             json=json.load(scorestream_data), status=200)

        # Because its mocked data, these dates are never used in the scorestream call

        today_date_time = datetime.strptime("2018-01-09 17:00:00", "%Y-%m-%d %H:%M:%S")
        monkeypatch.setattr('utils.utils.get_scheduler_offset',  lambda general_config: 60)

        current_date_time = datetime.now()
        run_time_id = "test_article"
        aah.process_article_request(customer_name="Test", fixed_date_time=today_date_time,
                                    game_range_days=0, delete_files=False,
                                    current_date_time=current_date_time,
                                    run_time_id=run_time_id,general_config=get_general_config())

        assert_object_exists(customer_name="Test",
                             run_time_id=run_time_id,
                             current_date_time=current_date_time)
        cleanup_s3()

        with open('output/test_ARTICLES_11_10_2017.txt', 'r') as out_file:
            content = out_file.read()
            print(content)
            assert True if 'ARTICLE CODE: 70' in content else False
            assert True if 'SPORT: football' in content else False
            assert True if 'GAMEID:\n999997' in content else False
            assert False if '[[' in content else True
        os.remove('output/test_ARTICLES_11_10_2017.txt')


def test_games_article_code_80(response_samples, dynamodb_tables, monkeypatch):

    with open('tests/data/article_code_80_football.json', 'r') as scorestream_data:

        response_samples.add(responses.GET, "http://scorestream.com/api",
                             json=json.load(scorestream_data), status=200)

        # Because its mocked data, these dates are never used in the scorestream call

        today_date_time = datetime.strptime("2018-01-10 17:00:00", "%Y-%m-%d %H:%M:%S")
        monkeypatch.setattr('utils.utils.get_scheduler_offset',  lambda general_config: 60)

        current_date_time = datetime.now()
        run_time_id = "test_article"
        aah.process_article_request(customer_name="Test", fixed_date_time=today_date_time,
                                    game_range_days=0, delete_files=False,
                                    current_date_time=current_date_time,
                                    run_time_id=run_time_id,general_config=get_general_config())

        assert_object_exists(customer_name="Test",
                             run_time_id=run_time_id,
                             current_date_time=current_date_time)
        cleanup_s3()

        with open('output/test_ARTICLES_11_11_2017.txt', 'r') as out_file:
            content = out_file.read()
            print(content)
            assert True if 'ARTICLE CODE: 80' in content else False
            assert True if 'SPORT: football' in content else False
            assert True if 'GAMEID:\n999998' in content else False
            assert False if '[[' in content else True
        os.remove('output/test_ARTICLES_11_11_2017.txt')


def test_games_article_code_90(response_samples, dynamodb_tables, monkeypatch):

    with open('tests/data/article_code_90_soccer.json', 'r') as scorestream_data:

        response_samples.add(responses.GET, "http://scorestream.com/api",
                             json=json.load(scorestream_data), status=200)

        # Because its mocked data, these dates are never used in the scorestream call

        today_date_time = datetime.strptime("2018-01-11 17:00:00", "%Y-%m-%d %H:%M:%S")
        monkeypatch.setattr('utils.utils.get_scheduler_offset',  lambda general_config: 60)

        current_date_time = datetime.now()
        run_time_id = "test_article"
        aah.process_article_request(customer_name="Test", fixed_date_time=today_date_time,
                                    game_range_days=0, delete_files=False,
                                    current_date_time=current_date_time,
                                    run_time_id=run_time_id,general_config=get_general_config())

        assert_object_exists(customer_name="Test",
                             run_time_id=run_time_id,
                             current_date_time=current_date_time)
        cleanup_s3()

        with open('output/test_ARTICLES_11_12_2017.txt', 'r') as out_file:
            content = out_file.read()
            print(content)
            assert True if 'ARTICLE CODE: 90' in content else False
            assert True if 'SPORT: soccer' in content else False
            assert True if 'GAMEID:\n999999' in content else False
            assert False if '[[' in content else True
        os.remove('output/test_ARTICLES_11_12_2017.txt')


def test_games_article_code_100(response_samples, dynamodb_tables, monkeypatch):

    with open('tests/data/article_code_100_football.json', 'r') as scorestream_data:

        response_samples.add(responses.GET, "http://scorestream.com/api",
                             json=json.load(scorestream_data), status=200)

        # Because its mocked data, these dates are never used in the scorestream call

        today_date_time = datetime.strptime("2018-01-12 17:00:00", "%Y-%m-%d %H:%M:%S")
        monkeypatch.setattr('utils.utils.get_scheduler_offset', lambda general_config: 60)

        current_date_time = datetime.now()
        run_time_id = "test_article"
        aah.process_article_request(customer_name="Test", fixed_date_time=today_date_time,
                                    game_range_days=0, delete_files=False,
                                    current_date_time=current_date_time,
                                    run_time_id=run_time_id,
                                    general_config=get_general_config()
                                    )

        assert_object_exists(customer_name="Test",
                             run_time_id=run_time_id,
                             current_date_time=current_date_time)
        cleanup_s3()

        with open('output/test_ARTICLES_11_13_2017.txt', 'r') as out_file:
            content = out_file.read()
            print(content)
            assert True if 'ARTICLE CODE: 100' in content else False
            assert True if 'SPORT: football' in content else False
            assert True if 'GAMEID:\n999990' in content else False
            assert False if '[[' in content else True
        os.remove('output/test_ARTICLES_11_13_2017.txt')


def test_out_of_state_games_filter(dynamodb_tables, games_teams_squad_list):
    logging.info("start of test for out_of_states_games_filter\n")
    logging.info("the games database contains games from different states TN,GA and OH, but with customer config set, it"
                "should pick up only TN games")

    games_list, teams_list, squad_list = games_teams_squad_list

    general_config = get_general_config()

    customer_config_table_name = general_config['customer_config_table']

    with open('tests/data/customer_config_out_of_state_filtering.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

        dynamo.dynamo_put_item(table_name=customer_config_table_name,entry=configuration)

        customer_test = customer_config.CustomerConfig(customer_name='Test_out_of_state', general_config=general_config)
        customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)
        customer_test.coverage_squad_list = customer_test.get_list_of_squads_by_sport()

        date_range = aah.get_date_range(customer_config=customer_test,
                                        today_datetime=datetime.strptime('2019-09-03 22:00:00', "%Y-%m-%d %H:%M:%S"),
                                        game_range_days=0)

        filtered_games, _ = aah.get_filtered_games(customer_config=customer_test,
                                                   date_range=date_range, games_list=games_list, teams_list=teams_list)

        assert list(map(lambda x: x['gameId'], filtered_games)) == [4,3] or \
               list(map(lambda x: x['gameId'], filtered_games)) == [3,4]


def test_filtering_games_squad_id(dynamodb_tables, games_teams_squad_list):
    logging.info("start of test for filtering_games_squad_id\n")
    logging.info("The games database contains games for squad ids 1010 and 1040 , but only 1010 should be picked")

    games_list, teams_list, squad_list = games_teams_squad_list

    general_config = get_general_config()

    customer_config_table_name = general_config['customer_config_table']

    with open('tests/data/customer_config_correct_squad_id_games_filtering.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

        dynamo.dynamo_put_item(table_name=customer_config_table_name,entry=configuration)

        customer_test = customer_config.CustomerConfig(customer_name='Test_squad_id_filter',
                                                       general_config=general_config)

        customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)
        customer_test.coverage_squad_list = customer_test.get_list_of_squads_by_sport()

        date_range = aah.get_date_range(customer_config=customer_test,
                                        today_datetime=datetime.strptime('2019-09-05 22:00:00', "%Y-%m-%d %H:%M:%S"),
                                        game_range_days=2)
        filtered_games, _ = aah.get_filtered_games(customer_config=customer_test,
                                                date_range=date_range, games_list=games_list, teams_list=teams_list)

        assert list(map(lambda x: x['gameId'], filtered_games)) == [1]


def test_filtering_tied_games(dynamodb_tables, games_teams_squad_list):
    logging.info("start of test for filtering_tied_games\n")
    logging.info("The games database contains invalid volleyball games for "
                "with tied score which should be filtered out")

    general_config = get_general_config()

    games_list, teams_list, squad_list = games_teams_squad_list

    customer_config_table_name = general_config['customer_config_table']

    with open('tests/data/customer_config_tied_games_filtering.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

        dynamo.dynamo_put_item(table_name=customer_config_table_name,entry=configuration)

        customer_test = customer_config.CustomerConfig(customer_name='Test_tied_games_filter',
                                                       general_config=general_config)
        customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)
        customer_test.coverage_squad_list = customer_test.get_list_of_squads_by_sport()

        date_range = aah.get_date_range(customer_config=customer_test,
                                        today_datetime=datetime.strptime('2019-09-05 22:00:00', "%Y-%m-%d %H:%M:%S"),
                                        game_range_days=2)
        filtered_games, _ = aah.get_filtered_games(customer_config=customer_test,
                                                date_range=date_range, games_list=games_list, teams_list=teams_list)

        assert 5 not in list(map(lambda x: x['gameId'], filtered_games))


def test_filtering_low_confidence_games(dynamodb_tables, games_teams_squad_list):
    logging.info("start of test for filtering_low_confidence_games\n")
    logging.info("The games database contains low confidence grade games\n")

    games_list, teams_list, squad_list = games_teams_squad_list

    general_config = get_general_config()

    customer_config_table_name = general_config['customer_config_table']

    with open('tests/data/customer_config_filtering_not_interested_sports.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

        dynamo.dynamo_put_item(table_name=customer_config_table_name,entry=configuration)

        customer_test = customer_config.CustomerConfig(customer_name='Test_not_interested_sports_filter',
                                                       general_config=general_config)
        customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)
        customer_test.coverage_squad_list = customer_test.get_list_of_squads_by_sport()

        date_range = aah.get_date_range(customer_config=customer_test,
                                        today_datetime=datetime.strptime('2019-09-30 22:00:00', "%Y-%m-%d %H:%M:%S"),
                                        game_range_days=2)
        filtered_games, _ = aah.get_filtered_games(customer_config=customer_test,
                                                date_range=date_range, games_list=games_list,
                                                teams_list=teams_list)

        assert not list(filtered_games)


def test_filtering_not_interested_games(dynamodb_tables, games_teams_squad_list):
    logging.info("start of test for filtering_not_interested_games\n")
    logging.info("Should only contain games of footabll as that is the interest and the databse contains volleyball and soccer games as well\n")

    games_list, teams_list, squad_list = games_teams_squad_list

    general_config = get_general_config()

    customer_config_table_name = general_config['customer_config_table']

    with open('tests/data/customer_config_filtering_not_interested_sports.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

        dynamo.dynamo_put_item(table_name=customer_config_table_name,entry=configuration)

        customer_test = customer_config.CustomerConfig(customer_name='Test_not_interested_sports_filter',
                                                       general_config=general_config)

        customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)
        customer_test.coverage_squad_list = customer_test.get_list_of_squads_by_sport()

        date_range = aah.get_date_range(customer_config=customer_test,
                                        today_datetime=datetime.strptime('2019-09-05 22:00:00', "%Y-%m-%d %H:%M:%S"),
                                        game_range_days=2)
        filtered_games, _ = aah.get_filtered_games(customer_config=customer_test,
                                                date_range=date_range, games_list=games_list,
                                                teams_list=teams_list)

        assert len(filtered_games) > 0
        assert list(filter(lambda x: x['sportName'] != 'football', filtered_games)) == []


def cleanup(customer_test, general_config):
    responses.add_passthru('https://')
    responses.add_passthru('http://')

    posted_assets_table_name = general_config['posted_assets_table']
    if os.path.exists(customer_test.article_output_file):
        os.remove(customer_test.article_output_file)
    html_file = customer_test.article_output_file.replace('.txt', '.html')
    if os.path.exists(html_file):
        os.remove(html_file)
    if customer_test.publishing_system and customer_test.auto_publish:
        blox_system_config = customer_test.publishing_system[0]
        wp_system_config = customer_test.publishing_system[1]

        handle_publish = publish_handler.HandlePublish(customer_config=customer_test)

        posted_items_1 = dynamo.dynamo_db_scan(table_name=posted_assets_table_name)

        blox_posted_items = list(filter(lambda x: 'blox' in x['type'], posted_items_1))
        wp_posted_items = list(filter(lambda x: 'wordpress' in x['type'], posted_items_1))

        for item in blox_posted_items:
            handle_publish._delete_from_blox(asset_id=item['id'], url=blox_system_config['urls'])
            dynamo.dynamo_delete_item(table_name=posted_assets_table_name, keys=['id', 'game_start_time'],
                                      vals=[item['id'], item['game_start_time']])

        for item in wp_posted_items:
            wp_id = item['id'].rsplit('_', 1)[1]
            handle_publish._delete_from_wordpress(asset_id=wp_id, system=wp_system_config)
            dynamo.dynamo_delete_item(table_name=posted_assets_table_name, keys=['id', 'game_start_time'],
                                      vals=[item['id'], item['game_start_time']])

    posted_items_1 = dynamo.dynamo_db_scan(table_name=posted_assets_table_name)

    for item in posted_items_1:
        dynamo.dynamo_delete_item(table_name=posted_assets_table_name, keys=['id', 'game_start_time'],
                                  vals=[item['id'], item['game_start_time']])
    return


@pytest.fixture
def dynamic_filter(loaded_dynamo, request):
    def fin():
        general_config = get_general_config()
        customer_test = customer_config.CustomerConfig(customer_name='Test_customer_dynamic_filter',
                                                       general_config=general_config)
        cleanup(customer_test=customer_test, general_config=general_config)

    request.addfinalizer(fin)
    yield


@pytest.fixture
def flag_test_system_on(loaded_dynamo, request):
    def fin():
        general_config = get_general_config()
        customer_test = customer_config.CustomerConfig(customer_name='Test_customer_test_system_on',
                                                       general_config=general_config)
        cleanup(customer_test=customer_test, general_config=general_config)

    request.addfinalizer(fin)
    yield

@pytest.fixture
def yearly_post_back(loaded_dynamo, request):
    def fin():
        general_config = get_general_config()
        customer_test = customer_config.CustomerConfig(customer_name='Test_customer_post_back',
                                                       general_config=general_config)
        cleanup(customer_test=customer_test, general_config=general_config)

    request.addfinalizer(fin)
    yield


def test_dynamic_filtering_content(dynamodb_tables, games_teams_squad_list, dynamic_filter):
    logging.info("filtering content based on dynamic content flag\n")

    responses.add_passthru('https://')
    responses.add_passthru('http://')

    general_config = get_general_config()

    games_list, teams_list, squad_list = games_teams_squad_list


    customer_config_table_name = general_config['customer_config_table']
    posted_assets_table_name = general_config['posted_assets_table']

    with open('tests/data/customer_config_dynamic_content_filtering.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

    dynamo.dynamo_put_item(table_name=customer_config_table_name, entry=configuration)

    customer_test = customer_config.CustomerConfig(customer_name='Test_customer_dynamic_filter',
                                                   general_config=general_config)
    customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)
    customer_test.coverage_squad_list = customer_test.get_list_of_squads_by_sport()

    # add date time to the slug of the blox slug

    customer_test.publishing_system[0]['json_payload_structure']['id'] += '_' + datetime.now().isoformat()
    customer_test.publishing_system[1]['data']['slug'] += '_' + datetime.now().isoformat()

    date_range = aah.get_date_range(customer_config=customer_test,
                                    today_datetime=datetime.strptime('2019-09-05 22:00:00', "%Y-%m-%d %H:%M:%S"),
                                    game_range_days=6)

    filtered_games, _ = aah.get_filtered_games(customer_config=customer_test, date_range=date_range,
                                            games_list=games_list, teams_list=teams_list)

    articles, stats_details, posted_urls, _ = aah.process_all_games(filtered_games, customer_test,
                                                                 run_time_id='default')

    logging.info("checking if all the contents are low dynamoc contents")
    for each_article in articles:
        assert each_article.l2_data.all_game_data.l2_data.article_content_dynamics == 'low'
    logging.info("Verified all the content dynamics are low\n")

    logging.info('verifying the article formatting capabilities\n')
    for each_article in articles:
        assert each_article.placeholder_text != ""
        assert each_article.plain_text != ""
        assert each_article.html_text != ""
        assert each_article.development_text != ""
        assert "[" not in each_article.html_text
        assert "]" not in each_article.html_text
        assert "[" not in each_article.plain_text
        assert "[" not in each_article.plain_text

    logging.info("completed the article formatting capabilities\n")

    logging.info("verifying the trailer boiler plates\n")

    for each_article in articles:
        assert customer_test.trailer_boiler_plate == each_article.trailer_boiler_plate
        assert each_article.trailer_boiler_plate['html'] in each_article.html_text
        assert each_article.trailer_boiler_plate['text'] in each_article.plain_text

    logging.info("completed verifying the trailer boiler plates\n")

    logging.info("verifying the text file\n")
    with open(customer_test.article_output_file,'r') as output_file:
        output = output_file.read()
        for each_article in articles:
            assert each_article.html_text_with_headline in output
    os.remove(customer_test.article_output_file)

    logging.info("verified the text files\n")

    logging.info("verifying the blox publishing\n")

    posted_items_1 = dynamo.dynamo_db_scan(table_name=posted_assets_table_name)

    blox_posted_items = list(filter(lambda x: 'blox' in x['type'],posted_items_1))
    wp_posted_items = list(filter(lambda x: 'wordpress' in x['type'],posted_items_1))

    # assert len(blox_posted_items) == 4
    logging.info("verified the blox publishing capabilities")
    logging.info("verifying the wp publishing capabilites")

    assert len(wp_posted_items) == 4

    logging.info("verified the wp pubishing")

    logging.info("verifying the stats details")
    assert stats_details['test_avail_wordpress'] == {201: 4}
    # assert stats_details['test_case_blox'] == {201: 4}

    logging.info("verified the stats details")

    logging.info("Will repost the same messages.This should result in 409")

    filtered_games, _ = aah.get_filtered_games(customer_config=customer_test, date_range=date_range,
                                            games_list=games_list,teams_list=teams_list)

    articles, stats_details, posted_urls, _ = aah.process_all_games(filtered_games, customer_test)

    logging.info("stats-details - %s", repr(stats_details))

    assert stats_details['test_avail_wordpress'] == {409: 4}
    # assert stats_details['test_case_blox'] == {409: 4}


def test_testsystem_flag_on(dynamodb_tables, games_teams_squad_list, flag_test_system_on):
    logging.info("filtering content based on dynamic content flag\n")

    responses.add_passthru('https://')
    responses.add_passthru('http://')

    games_list, teams_list, squad_list = games_teams_squad_list

    general_config = get_general_config()

    customer_config_table_name = general_config['customer_config_table']
    posted_assets_table_name = general_config['posted_assets_table']

    with open('tests/data/customer_config_test_system_flag_on.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

    dynamo.dynamo_put_item(table_name=customer_config_table_name, entry=configuration)

    customer_test = customer_config.CustomerConfig(customer_name='Test_customer_test_system_on',
                                                   general_config=general_config)

    customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)
    customer_test.coverage_squad_list = customer_test.get_list_of_squads_by_sport()

    # add date time to the slug of the blox slug

    customer_test.publishing_system[0]['json_payload_structure']['id'] += '_' + datetime.now().isoformat()
    customer_test.publishing_system[1]['data']['slug'] += '_' + datetime.now().isoformat()

    date_range = aah.get_date_range(customer_config=customer_test,
                                    today_datetime=datetime.strptime('2019-09-05 22:00:00', "%Y-%m-%d %H:%M:%S"),
                                    game_range_days=6)

    filtered_games, _ = aah.get_filtered_games(customer_config=customer_test, date_range=date_range,
                                            games_list=games_list, teams_list=teams_list)

    articles, stats_details, posted_urls, _ = aah.process_all_games(filtered_games, customer_test)

    logging.info("checking the number of articles on text file is 4 and published is 1")

    logging.info("verifying the text file\n")
    with open(customer_test.article_output_file,'r') as output_file:
        output = output_file.read()
        assert len(articles) == 4
        for each_article in articles:
            assert each_article.html_text_with_headline in output
    logging.info("verified the text files\n")

    html_file = customer_test.article_output_file.replace('.txt', '.html')
    os.remove(html_file)

    logging.info("verifying the blox publishing\n")

    posted_items_1 = dynamo.dynamo_db_scan(table_name=posted_assets_table_name)

    blox_posted_items = list(filter(lambda x: 'blox' in x['type'],posted_items_1))
    wp_posted_items = list(filter(lambda x: 'wordpress' in x['type'],posted_items_1))

    # assert len(blox_posted_items) == 1
    logging.info("verified the blox publishing capabilities")
    logging.info("verifying the wp publishing capabilites")

    assert len(wp_posted_items) == 1

    logging.info("verified the wp pubishing")

    logging.info("verifying the stats details")
    assert stats_details['test_avail_wordpress'] == {201: 1}
    # assert stats_details['test_case_blox'] == {201: 1}

    logging.info("verified the stats details")


def test_send_mail():
    try:
        # utils.send_mail(message='test message\n', send_from='staconsulting@outlook.com', send_to=['jothi@abundat.com'],
        #                 subject='test')
        utils.send_aws_email(msg_txt='test message\n', send_from='content@ledeai.com', send_to=['jothi@abundat.com'],
                        subject='test')
    except Exception as e:
        logging.info("this is the exception %s", repr(e))
        assert False


def test_yearly_post_back(yearly_post_back, games_teams_squad_list):
    general_config = get_general_config()
    customer_config_table_name = general_config['customer_config_table']
    posted_assets_table_name = general_config['posted_assets_table']
    posted_assets_table_name_alt = general_config['posted_assets_table_alt']

    games_list, teams_list, squad_list = games_teams_squad_list

    with open('tests/data/customer_config_yearly_post_back.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

    dynamo.dynamo_put_item(table_name=customer_config_table_name, entry=configuration)

    with open('tests/data/posted_assets.json') as posted_assets:
        posted_assets_data = json.load(posted_assets)

    for each_asset in posted_assets_data['yearly_assets']:
        dynamo.dynamo_put_item(table_name=posted_assets_table_name, entry=each_asset)

    for each_asset in posted_assets_data['yearly_assets_alt']:
        dynamo.dynamo_put_item(table_name=posted_assets_table_name_alt, entry=each_asset)

    customer_test = customer_config.CustomerConfig(customer_name='Test_customer_post_back',
                                                   general_config=general_config)
    customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)
    customer_test.coverage_squad_list = customer_test.get_list_of_squads_by_sport()

    date_range = aah.get_date_range(customer_config=customer_test,
                                    today_datetime=datetime.strptime('2019-10-03 20:00:00', "%Y-%m-%d %H:%M:%S"),
                                    game_range_days=6)

    filtered_games, _ = aah.get_filtered_games(customer_config=customer_test, date_range=date_range,
                                            games_list=games_list, teams_list=teams_list)

    articles, stats_details, posted_urls, _ = aah.process_all_games(filtered_games, customer_test)

    assert articles[0].deep_link_article.yearly_article['txt'] is not ''
    assert articles[0].deep_link_article.yearly_article['html'] is not ''
    assert articles[0].deep_link_article.weekly_articles['txt'] is ''
    assert articles[0].deep_link_article.weekly_articles['html'] is ''


def test_weekly_post_back(yearly_post_back, games_teams_squad_list):

    general_config = get_general_config()

    customer_config_table_name = general_config['customer_config_table']
    posted_assets_table_name = general_config['posted_assets_table']
    posted_assets_table_name_alt = general_config['posted_assets_table_alt']

    games_list, teams_list, squad_list = games_teams_squad_list

    with open('tests/data/customer_config_yearly_post_back.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

    dynamo.dynamo_put_item(table_name=customer_config_table_name, entry=configuration)

    customer_test = customer_config.CustomerConfig(customer_name='Test_customer_post_back', general_config=general_config)
    customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)
    customer_test.coverage_squad_list = customer_test.get_list_of_squads_by_sport()

    date_range = aah.get_date_range(customer_config=customer_test,
                                    today_datetime=datetime.strptime('2019-10-03 20:00:00', "%Y-%m-%d %H:%M:%S"),
                                    game_range_days=6)

    filtered_games, _ = aah.get_filtered_games(customer_config=customer_test, date_range=date_range,
                                            games_list=games_list, teams_list=teams_list)

    with open('tests/data/posted_assets.json') as posted_assets:
        posted_assets_data = json.load(posted_assets)

    for each_asset in posted_assets_data['weekly_assets']:
        dynamo.dynamo_put_item(table_name=posted_assets_table_name, entry=each_asset)

    for each_asset in posted_assets_data['weekly_assets_alt']:
        dynamo.dynamo_put_item(table_name=posted_assets_table_name_alt, entry=each_asset)

    articles, stats_details, posted_urls, _ = aah.process_all_games(game_list=filtered_games,
                                                                 customer_config=customer_test
                                                                )

    assert articles[0].deep_link_article.yearly_article['txt'] is ''
    assert articles[0].deep_link_article.yearly_article['html'] is ''
    assert articles[0].deep_link_article.weekly_articles['txt'] is not ''
    assert articles[0].deep_link_article.weekly_articles['html'] is not ''


def test_yearly_weekly_post_back(yearly_post_back, games_teams_squad_list):
    general_config = get_general_config()

    customer_config_table_name = general_config['customer_config_table']
    posted_assets_table_name = general_config['posted_assets_table']
    posted_assets_table_name_alt = general_config['posted_assets_table_alt']

    games_list, teams_list, squad_list = games_teams_squad_list

    with open('tests/data/customer_config_yearly_post_back.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

    dynamo.dynamo_put_item(table_name=customer_config_table_name, entry=configuration)

    with open('tests/data/posted_assets.json') as posted_assets:
        posted_assets_data = json.load(posted_assets)

    for each_asset in posted_assets_data['weekly_assets']:
        dynamo.dynamo_put_item(table_name=posted_assets_table_name, entry=each_asset)

    for each_asset in posted_assets_data['yearly_assets']:
        dynamo.dynamo_put_item(table_name=posted_assets_table_name, entry=each_asset)

    for each_asset in posted_assets_data['weekly_assets_alt']:
        dynamo.dynamo_put_item(table_name=posted_assets_table_name_alt, entry=each_asset)

    for each_asset in posted_assets_data['yearly_assets_alt']:
        dynamo.dynamo_put_item(table_name=posted_assets_table_name_alt, entry=each_asset)

    customer_test = customer_config.CustomerConfig(customer_name='Test_customer_post_back',
                                                   general_config=general_config)
    customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)
    customer_test.coverage_squad_list = customer_test.get_list_of_squads_by_sport()

    date_range = aah.get_date_range(customer_config=customer_test,
                                    today_datetime=datetime.strptime('2019-10-03 20:00:00', "%Y-%m-%d %H:%M:%S"),
                                    game_range_days=6)

    filtered_games, _ = aah.get_filtered_games(customer_config=customer_test, date_range=date_range,
                                            games_list=games_list, teams_list=teams_list)

    articles, stats_details, posted_urls, _ = aah.process_all_games(game_list=filtered_games,
                                                                 customer_config=customer_test)

    assert articles[0].deep_link_article.yearly_article['txt'] is not ''
    assert articles[0].deep_link_article.yearly_article['html'] is not ''
    assert articles[0].deep_link_article.weekly_articles['txt'] is not ''
    assert articles[0].deep_link_article.weekly_articles['html'] is not ''

@pytest.fixture
def headline_score(loaded_dynamo, request):
    def fin():
        general_config = get_general_config()
        customer_test = customer_config.CustomerConfig(customer_name='Test_customer_headline_score',
                                                       general_config=general_config)
        cleanup(customer_test=customer_test, general_config=general_config)

    request.addfinalizer(fin)
    yield


def test_headline_scores(headline_score, games_teams_squad_list):
    general_config = get_general_config()
    customer_config_table_name = general_config['customer_config_table']

    games_list, teams_list, squad_list = games_teams_squad_list
    
    with open('tests/data/customer_config_headline_score.json') as config_file:
        configuration = json.load(config_file, parse_float=Decimal)

    dynamo.dynamo_put_item(table_name=customer_config_table_name, entry=configuration)

    customer_test = customer_config.CustomerConfig(customer_name='Test_customer_headline_score',
                                                   general_config=general_config)

    customer_test.coverage_team_list = customer_test.get_list_of_teams_by_sport(team_list=teams_list)
    customer_test.coverage_squad_list = customer_test.get_list_of_squads_by_sport()

    date_range = aah.get_date_range(customer_config=customer_test,
                                    today_datetime=datetime.strptime('2019-10-03 20:00:00', "%Y-%m-%d %H:%M:%S"),
                                    game_range_days=6)

    filtered_games, _ = aah.get_filtered_games(customer_config=customer_test, date_range=date_range,
                                            games_list=games_list, teams_list=teams_list)

    articles, stats_details, posted_urls, _ = aah.process_all_games(filtered_games, customer_test)

    assert articles[0].l2_data.base_score_string in articles[0].headline
