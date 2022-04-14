"""
This module provides all the class defintioms for Score stream games and teams that needs to be
uploaded to the database.

"""
import logging


logger = logging.getLogger(__name__)


class SSGames:
    
    def __init__(self, full_result, from_ss):
        self.full_result = full_result
        self.from_ss = from_ss
    
    def get_collections(self):
        if self.from_ss is True:
            return self.full_result['collections']
    
    def del_unnecessary(self, attributes, coll):
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
        if len(keys) > len(vals):
            logging.error("len of keys and len of vals are different, hence skipping")
            
        for i in range(len(keys)):
            coll[keys[i]] = vals[i]
        return coll
    
    def filter_text(self, text, num_chars, from_left, separator=None):
        t = ''
        if from_left is True: t=text[0:num_chars]
        else: t = text[-num_chars:]
        
        if separator is not None: return t.split('-')
        else: return t
        
    def convert_vals_to_str(self, entry):
        if 'aspectRatio' in entry:
            return (str(entry['aspectRatio']),'NONE_TEXT')
        if 'longitude' not in entry:
            return (0,0)
        else:
            long = str(entry['longitude'])
            lat = str(entry['latitude'])
            return (long, lat)


class SSSortGames(SSGames):
    
    def __init__(self, full_result, from_ss, del_keys=None):
        super().__init__(full_result, from_ss)
        self.del_keys = del_keys
        
    def get_game_list(self):
        return self.get_collections()['gameCollection']['list']
    
    def get_num_games(self):
        return len(self.get_game_list())
    
    def process_ss_game_data(self, ss_game):
        logging.info("Processing_ss_game_data for game %d\n", ss_game['gameId'])
        away_final_score=9999
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
            
        date_arr = self.filter_text(text=ss_game['startDateTime'], num_chars=10,from_left=True,separator='-')
        game_year = int(date_arr[0])
        game_month = int(date_arr[1])
        game_day = int(date_arr[2])
            
        self.del_keys = []
        self.del_keys = self.del_keys + ['lastScore','hideLevel','useGameClock','rankBonus',
                                         'scheduleCategoryId','branchedUsers', 'longitude', 'latitude']
            
        self.del_unnecessary(self.del_keys,ss_game)
            
        self.add_values_to_dict(keys=['awayTeamScore', 'homeTeamScore', 'confidenceGrade', 'stoppageStatusId',
                                      'stoppageMessage', 'gameYear', 'gameMonth', 'gameDay', 'longitude', 'latitude'],
                                vals=[away_final_score, home_final_score,confidence_grade,stoppage_id,stoppage_message,
                                      int(game_year),int(game_month),int(game_day), lat_long[0], lat_long[1]],
                                coll=ss_game, func_name='process_ss_game_data')

        logging.info("Completed  Processing_ss_game_data for game %d\n", ss_game['gameId'])

        return ss_game
    
    def get_processed_game_list(self):
        gl = self.get_game_list()
        game_list = []
        for ss_game in gl:
            if 'lastScore' not in ss_game or self.from_ss is False:
                logging.info("Lastscore is not found for game %d", ss_game['gameId'])
                game_list.append(ss_game)
            elif 'lastScore' in ss_game and self.from_ss is True:
                # do not upload the games to the database which are not completed yet
                if ss_game['lastScore']['gameSegmentId'] == 19999:
                    game_list.append(self.process_ss_game_data(ss_game))
                else:
                    logging.info("Game in Progress or yet to be started for %d\n", ss_game['gameId'])
        return game_list


class SSSortTeams(SSGames):
    
    def __init__(self, full_result, from_ss):
        super().__init__(full_result, from_ss)
        
    def get_teams_list(self):
        if self.from_ss is True: 
            coll = super().get_collections()['teamCollection']['list']
            for item in coll:
                self.del_unnecessary(['latitude', 'longitude'], coll=item)
                lat_long = self.convert_vals_to_str(item)
                self.add_values_to_dict(keys=['longitude','latitude'],vals=[lat_long[0], lat_long[1]],coll=item,func_name='sort_teams')
                state = item['state']
                del item['state']
                item['home_state'] = state
        return coll
    
    def get_team_pictures_list(self):
        from utils import utils
        coll = super().get_collections()['teamPictureCollection']['list']
        for item in coll:
            lat_long = self.convert_vals_to_str(item)
            self.del_unnecessary(['aspectRatio'], coll=item)
            self.add_values_to_dict(keys=['aspectRatio'],vals=[lat_long[0]],coll=item,func_name='get_team_pictures_list')
        if self.from_ss is True: return utils.de_dup_list(coll)

