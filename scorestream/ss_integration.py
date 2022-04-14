"""
This module is the core module which would be called by the article handler to sort, massage the
data and uploading them to the dynamo db.

"""
import logging
from db import dynamo
from datetime import datetime, timedelta
from scorestream import colors
from scorestream import ss_url_requests, ss_data_sort
from scorestream import squads
from copy import deepcopy


logger = logging.getLogger(__name__)


def get_complete_result(method, params):
    logging.info("Get complete result started\n")
    ss_url = ss_url_requests.ss_url_requests(method=method, method_key='method',
                                             params=params)
    request = ss_url.make_request()
    logging.info("Get complete result completed\n")
    logging.info("The result is %s", repr(request.json()['result']['gameIds']))
    return request.json()['result']


def post_result(method, params):
    logging.info("Get complete result started\n")
    ss_url = ss_url_requests.ss_url_requests(method=method, method_key='method',
                                             params=params)
    response = ss_url.post_request()
    logging.info("post result completed\n")
    return response.json()


def get_games(from_ss, result):
    logging.info("Extracting games from the full result \n")
    game_list = ss_data_sort.SSSortGames(from_ss=from_ss,full_result=result)
    return game_list.get_processed_game_list()


def get_teams(from_ss,result):
    logging.info("Extracting teams from the full result \n")
    teams = ss_data_sort.SSSortTeams(from_ss=from_ss,full_result=result)
    return teams.get_teams_list()


def get_team_pics(from_ss,result):
    logging.info("Extracting team pics from the full result \n")
    teams = ss_data_sort.SSSortTeams(from_ss=from_ss,full_result=result)
    return teams.get_team_pictures_list()


def get_colors(result):
    logging.info("Extracting color list from the full result \n")
    color_list = colors.Colors(complete_result=result)
    return color_list.get_colors_list_from_ss()


def get_squads(result:list):
    logging.info("Extracting squad list from the full result \n")
    squad_list = squads.Squads(complete_result=result)
    return squad_list.get_squad_list()


def check_for_true_in_bool_list(l:list):
    for i in range(len(l)):
        if l[i][0] is True: return i
    return None


def sort_and_upload_result(result:list,from_ss):
    logging.info("Sorting and uploading the fetched result \n")
    recommended = [(get_squads(result=result), 'RS_AI_SS_SQUADS'),
                   (get_games(from_ss,result), 'RS_AI_SS_GAMES'),
                   (get_teams(from_ss,result), 'RS_AI_SS_TEAMS'),
                   (get_team_pics(from_ss,result), 'RS_AI_SS_TEAM_PICS')]
    
    for item in recommended:
        logging.info("Uploading to the %s table", item[1])
        dynamo.dynamo_batch_put_item(entry=item[0], table_name=item[1])
        logging.info("Uploading to the %s table complete", item[1])
    return True


def get_result_and_upload(method:str, params:dict):
    result = get_complete_result(method=method,params=params)
    # sort_and_upload_result(from_ss=True, result=result)
    return result


def get_games_for_location(location_arr, date_range):

    api_key = 'd572dff0-1e62-4f8d-962b-589bed0d6e24'

    complete_result = {}

    for l in location_arr:
        latitude = l[0]
        longitude = l[1]
        location = {'latitude': latitude, 'longitude': longitude}
        start_date = datetime.strptime(date_range[0], "%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(date_range[1], "%Y-%m-%d %H:%M:%S")
        while start_date < end_date:
            if end_date > start_date + timedelta(days=10):
                range_end_date = start_date + timedelta(days=10)
            else:
                range_end_date = end_date
            parameters = {
                'location': location,
                'apiKey': api_key,
                'count': 10000,
                'afterDateTime': start_date.strftime("%Y-%m-%d %H:%M:%S"),
                'beforeDateTime': range_end_date.strftime("%Y-%m-%d %H:%M:%S"),
            }
            try:
                result = get_result_and_upload(method='recommended.broadcast.games.search', params=parameters)
                complete_result = update_complete_result(complete_result, result)
            except Exception as e:
                logging.exception("encountered exception during fetching games from scorestream" + repr(e))
                result = {}
            start_date = range_end_date
        logging.info("Getting games for location %f and %f", latitude, longitude)
    return complete_result


def update_complete_result(complete_result, result):

    logging.info("Updating result with complete result")
    if not complete_result:
        complete_result = deepcopy(result)
    else:
        if 'collections' in result:
            for key in result['collections']:
                if 'list' in result['collections'][key] and type(result['collections'][key]['list']) is list:
                    if key not in complete_result['collections']:
                        complete_result['collections'][key] = {'list': []}
                    complete_result['collections'][key]['list'] = complete_result['collections'][key]['list'] + result['collections'][key]['list']
    return complete_result


def post_games_posts_add(game_id, postback_text):
    logging.info("Started the games postback")
    params = {
        "apiKey": "d572dff0-1e62-4f8d-962b-589bed0d6e24",
        "accessToken": "31ea2602-0123-476b-83bf-4b34da6261fd",
        "gameId": game_id,
        "userText": postback_text
    }

    response = post_result(method='games.posts.add', params=params)
    logging.info("completed the games post back for game id %d", game_id)
    logging.info("The url with the games post is %s", repr(response['result']['collections']['gamePostCollection']))
    return response['result']

