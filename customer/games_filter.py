"""
This module will filter the games based on the parameters given in the customer config , date of
games played etc and will output True if the game matches those conditions.

"""
import json
import logging
from db import dynamo
from datetime import datetime
import traceback
from copy import deepcopy



# get a logger at the module level

logger = logging.getLogger(__name__)


class GameFilter:
    def __init__(self, customer_config, date_range, games_list, teams_list):
        self.article_run_detailed_info = []
        self.customer_config = customer_config
        self.date_range = date_range
        self.general_config = self.customer_config.general_config
        self._update_sports_season()
        self.games_list = self.get_games_list(games_list, teams_list)

    def _update_sports_season(self):
        self.sports_season = self.general_config['sports_season']
        if hasattr(self.customer_config, 'sports_season') and self.customer_config.sports_season:
            self.sports_season.update(self.customer_config.sports_season)

    def is_valid_game(self, game, game_detailed_info):
        valid_game = False
        # create a team id list for sports specific and as well as default one so that if there are no sports specific
        # coverage list, we would end up using the default one

        filtered_team_list = self.get_list_for_sport(self.customer_config.coverage_team_list, game['sportName'])

        if game is None:
            logging.info("GAME WITH GAME ID %d IS NONE ", game['gameId'])
        elif 'lastScore' not in game:
            game_detailed_info['is_valid'] = False
            game_detailed_info['invalid_reason'] = 'Lastscore not found'
            logging.info("Lastscore is not found for game %d", game['gameId'])
        elif game['sportName'] not in self.customer_config.sports_interested:
            game_detailed_info['is_valid'] = False
            game_detailed_info['invalid_reason'] = 'SportName not Interested'
            logging.info("Game id - %d with sportname %s is not an interested sport", game['gameId'], game['sportName'])
        
        elif game['startDateTime'] < self.date_range[0] or game['startDateTime'] > self.date_range[1]:
            game_detailed_info['is_valid'] = False
            game_detailed_info['invalid_reason'] = 'Startdatetime not within the expected range'
            logging.info("game id - %d with startdatetime %s is not with range %s and %s", game['gameId'], game['startDateTime'], self.date_range[0], self.date_range[1])

        elif game['homeSquadId'] not in self.get_list_for_sport(self.customer_config.coverage_squad_list, game['sportName']):
            game_detailed_info['is_valid'] = False
            game_detailed_info['invalid_reason'] = 'Does not have the right squad id'
            logging.info("Game Does not have the right Squadid")

        elif (game['homeTeamScore'] == 0 and game['awayTeamScore'] == 0 and game['sportName'] not in
                self.general_config['tie_games_allowed']):
            game_detailed_info['is_valid'] = False
            game_detailed_info['invalid_reason'] = 'Tied Game Not allowed'
            logging.info("UNWRITTEN: SCORES ZERO FOR GAME ID %d", game['gameId'])

        elif 'stoppageStatusId' in game and game['stoppageStatusId'] and game[
            'stoppageStatusId'] != 9999:
            game_detailed_info['is_valid'] = False
            game_detailed_info['invalid_reason'] = 'Game has stoppage status id'
            logging.info("Game has stoppage status id - %s", str(game['stoppageStatusId']))

        elif 'confidenceGrade' in game and game['confidenceGrade'] < 80:
            game_detailed_info['is_valid'] = False
            game_detailed_info['invalid_reason'] = 'Confidence score less than threshold'

            logging.info("Game has less than 80 confidence with ID %d", game['gameId'])
        elif 'lastScore' in game and game['lastScore']['gameSegmentId'] != 19999:
            game_detailed_info['is_valid'] = False
            game_detailed_info['invalid_reason'] = 'Game in Progress or yet to be started'
            logging.info("Game in Progress or yet to be started for %d\n", game['gameId'])

        elif filtered_team_list['teams']:
            if filtered_team_list['exclude_teams']:
                if (game['awayTeamId'] in filtered_team_list['exclude_teams']
                        or game['homeTeamId'] in filtered_team_list['exclude_teams']):
                    game_detailed_info['is_valid'] = False
                    game_detailed_info['invalid_reason'] = 'Game does not belong to market'
                    logging.info("GAME DOES NOT BELONG To MARKET %d", game['gameId'])
                    valid_game = False
                else:
                    if not (game['awayTeamId'] in filtered_team_list['teams'] or game['homeTeamId']
                            in filtered_team_list['teams']):
                        game_detailed_info['is_valid'] = False
                        game_detailed_info['invalid_reason'] = 'Game does not belong to market'
                        logging.info("GAME DOES NOT BELONG To MARKET %d", game['gameId'])
                        valid_game = False
                    else:
                        game_detailed_info['is_valid'] = True
                        valid_game = True
            else:
                if not (game['awayTeamId'] in filtered_team_list['teams'] or game['homeTeamId']
                        in filtered_team_list['teams']):
                    game_detailed_info['is_valid'] = False
                    game_detailed_info['invalid_reason'] = 'Game does not belong to market'
                    logging.info("GAME DOES NOT BELONG To MARKET %d", game['gameId'])
                else:
                    game_detailed_info['is_valid'] = True
                    valid_game = True
        if valid_game:
            valid_game = False
            if str(game['sportName']):
                sport_name = str(game['sportName']).lower()
                game_month = datetime.strptime(game['startDateTime'], '%Y-%m-%d %H:%M:%S').strftime("%-m")
                list_sports = self.sports_season[game_month]

                for each_sport in list_sports:
                    if str(each_sport).startswith(sport_name):
                        game_detailed_info['is_valid'] = True
                        valid_game = True
                        break
                if valid_game is False:
                    game_detailed_info['is_valid'] = False
                    game_detailed_info['invalid_reason'] = 'Game starttime is not covered under this season'
                    logging.info("Game %s for the starttime %s is not covered under the season",
                                str(game['gameId']), game['startDateTime'])

        return valid_game

    @staticmethod
    def get_list_for_sport(value_list, sport_name):
        if sport_name in value_list:
            return value_list[sport_name]
        elif 'all' in value_list:
            return value_list['all']
        else:
            return []

    def get_games_list(self, games_list, teams_list):
        logging.info("Obtaining valid game for the team")
        logging.info("the total number of games scanned is %d", len(games_list))
        valid_games = self._get_valid_games(games_list, teams_list)
        logging.info("the total number of games valid is %d", len(valid_games))
        return valid_games

    def _get_valid_games(self, games, teams):
        valid_games = []

        teams_dict = {x['teamId']:x for x in teams}

        for game in games:
            try:
                self.process_ss_game_data(game)
                game_detailed_info = self.update_game_detailed_info(game=game, teams_dict=teams_dict)
                if self.is_valid_game(game, game_detailed_info):
                    valid_games.append(game)
                self.article_run_detailed_info.append(game_detailed_info)
            except:
                logging.error("Error processing game -%s", repr(game))
                continue

        valid_games.sort(key=lambda x: x.get('homeSquadId'))
        return valid_games

    def process_ss_game_data(self, ss_game):
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

        lat_long = self.convert_vals_to_str(ss_game)

        date_arr = self.filter_text(text=ss_game['startDateTime'], num_chars=10, from_left=True, separator='-')
        game_year = int(date_arr[0])
        game_month = int(date_arr[1])
        game_day = int(date_arr[2])

        self.del_keys = []
        self.del_keys = self.del_keys + ['hideLevel', 'useGameClock', 'rankBonus',
                                         'scheduleCategoryId', 'branchedUsers', 'longitude', 'latitude']

        self.del_unnecessary(self.del_keys, ss_game)

        self.add_values_to_dict(keys=['awayTeamScore', 'homeTeamScore', 'confidenceGrade', 'stoppageStatusId',
                                      'stoppageMessage', 'gameYear', 'gameMonth', 'gameDay', 'longitude', 'latitude'],
                                vals=[away_final_score, home_final_score, confidence_grade, stoppage_id,
                                      stoppage_message,
                                      int(game_year), int(game_month), int(game_day), lat_long[0], lat_long[1]],
                                coll=ss_game, func_name='process_ss_game_data')

        logging.info("Completed  Processing_ss_game_data for game %d\n", ss_game['gameId'])

        return ss_game

    @staticmethod
    def update_game_detailed_info(game, teams_dict):
        logging.info("Updating detailed info for %s", game['gameId'])
        game_detailed_info = deepcopy(game)

        for x in ['home', 'away']:
            try:
                if x + 'TeamId' in game_detailed_info and game_detailed_info[x + 'TeamId'] and \
                        game_detailed_info[x + 'TeamId'] in teams_dict:
                    game_detailed_info[x + 'TeamName'] = teams_dict[game_detailed_info[x + 'TeamId']]['teamName']
                    game_detailed_info[x + 'TeamCity'] = teams_dict[game_detailed_info[x + 'TeamId']]['city']
                    game_detailed_info[x + 'TeamUrl'] = teams_dict[game_detailed_info[x + 'TeamId']]['url']
                    game_detailed_info[x + 'TeamState'] = teams_dict[game_detailed_info[x + 'TeamId']]['state']
            except Exception:
                logging.exception("Error updating the %s team id details ", x)
        return game_detailed_info

    @staticmethod
    def del_unnecessary(attributes, coll):
        '''
        attributes is [str] with the keys to delete. coll is the dict.
        '''
        for item in attributes:
            if item in coll:
                del coll[item]
        return coll

    def add_values_to_dict(self, keys, vals, coll, func_name):
        '''
        keys are a [str], vals are [vars], coll is the dict they're being added to
        '''
        for i in range(len(keys)):
            coll[keys[i]] = vals[i]
        return coll

    def filter_text(self, text, num_chars, from_left, separator=None):
        t = ''
        if from_left is True:
            t = text[0:num_chars]
        else:
            t = text[-num_chars:]

        if separator is not None:
            return t.split('-')
        else:
            return t

    def convert_vals_to_str(self, entry):
        if 'aspectRatio' in entry:
            return (str(entry['aspectRatio']), 'NONE_TEXT')
        if 'longitude' not in entry:
            return (0, 0)
        else:
            long = str(entry['longitude'])
            lat = str(entry['latitude'])
            return (long, lat)


