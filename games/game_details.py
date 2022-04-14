"""
This module constructs a Game Object with all the necessary details of a game as retrieved
from the dynamo db.

"""

import logging
from utils import dates

logger = logging.getLogger(__name__)


class Game:
    def __init__(self, game_dict:dict):
        self.game_dict = game_dict
        
        self.warning_flags = {}
        self.kill_flags = {}

        self.ap_special_name = self.__get_value_for_key('apSpecialName')
        self.away_squad_id = self.__get_value_for_key('awaySquadId')
        self.away_team_cheers = self.__get_value_for_key('awayTeamCheers')
        self.away_team_id = self.__get_value_for_key('awayTeamId')
        self.away_team_score = self.__get_value_for_key('awayTeamScore')
        self.box_scores = self.__convert_box_score(bs=self.__get_value_for_key('boxScores'))
        self.confidence_grade = self.__get_value_for_key('confidenceGrade')
        self.game_day = self.__get_value_for_key('gameDay')
        self.game_month = self.__get_value_for_key('gameMonth')
        self.game_year = self.__get_value_for_key('gameYear')
        self.game_id = self.__get_value_for_key('gameId')
        self.game_segment_type = self.__get_value_for_key('gameSegmentType')
        self.game_segment_type_id = self.__get_value_for_key('gameSegmentTypeId')
        self.game_title = self.__get_value_for_key('gameTitle')

        self.home_squad_id = self.__get_value_for_key('homeSquadId')
        self.home_team_cheers = self.__get_value_for_key('homeTeamCheers')
        self.home_team_id = self.__get_value_for_key('homeTeamId')
        self.home_team_score = self.__get_value_for_key('homeTeamScore')
        self.latitude = self.__get_value_for_key('latitude')
        self.local_game_time_zone = self.__get_value_for_key('localGameTimezone')
        self.longitude = self.__get_value_for_key('longitude')
        self.sport_id = self.__get_value_for_key('sportId')
        self.sport_name = self.__get_value_for_key('sportName')
        self.start_date_time = self.__get_value_for_key('startDateTime')
        self.stoppage_message = self.__get_value_for_key('stoppageMessage')
        self.stoppage_status_id = self.__get_value_for_key('stoppageStatusId')
        self.total_chats = self.__get_value_for_key('totalChats')
        self.total_pictures = self.__get_value_for_key('totalPictures')
        self.total_posts = self.__get_value_for_key('totalPosts')
        self.total_quick_scores = self.__get_value_for_key('totalQuickScores')
        self.url = self.__get_value_for_key('url')
        self.venue_id = self.__get_value_for_key('venueId')

        self.utc_start_date_time = self.start_date_time
        # This will convert all the UTC date times to the local times for game_day, game_month
        self.__get_localised_dates()

        self.home_team_won = self.__determine_winning_team()
        
        self.winning_score_key = self.__get_score_key()[0]
        self.losing_score_key = self.__get_score_key()[1]
        
        self.game_day_str = self.__get_game_day_str()
        logging.info("Its a %s game between %d and %d played on %s at %d", self.sport_name, self.home_team_id,
                    self.away_team_id, self.game_day_str, self.venue_id)
        logging.info("HomeTeamscore - AwayTeamScore is %d-%d", self.home_team_score, self.away_team_score)
        logging.info("The Source URL for the game would be %s", self.url)
        logging.info("Completed the initialization of the RS_GAMES for game %d", self.game_id)

    def __get_game_day_str(self):
        return dates.Dates().get_day_of_week(year=self.game_year, month=self.game_month, day=self.game_day)
        
    def __get_value_for_key(self,key):
        if self.game_dict is None:
            logging.info("Game dict is None\n")
            return None
        elif key in self.game_dict:
            logging.debug("Found %s in game_dict\n", key)
            return self.game_dict[key]
        else:
            logging.debug("Missing value for key %s", key)
            self.warning_flags["MISSING_VALUE_FOR_KEY"] = key
            return None

    def __convert_box_score(self, bs: dict):
        for item in bs:
            if 'homeTeamScore' in item and type(item['homeTeamScore']) is str:
                item['homeTeamScore'] = 0
            if 'awayTeamScore' in item and type(item['awayTeamScore']) is str:
                item['awayTeamScore'] = 0
        return bs

    def __determine_winning_team(self):
        if self.home_team_score > self.away_team_score:
            logging.info("Home team is the winning team %d-%d\n", self.home_team_score, self.away_team_score)
            return True
        elif self.home_team_score < self.away_team_score:
            logging.info("Away team is the winning team %d-%d\n", self.away_team_score, self.home_team_score)
            return False
        elif self.home_team_score == self.away_team_score:
            logging.info("Neither team is the winning team %d-%d\n", self.home_team_score, self.away_team_score)
            return None
        
    def __get_score_key(self):
        if self.__determine_winning_team() is True:
            return 'homeTeamScore', 'awayTeamScore'
        else:
            return 'awayTeamScore', 'homeTeamScore'

    def __get_localised_dates(self):
        game_local_time = dates.Dates().utc_to_local(self.start_date_time, self.local_game_time_zone)
        (self.game_year, self.game_month, self.game_day, _, _, _, _, _, _) = game_local_time.timetuple()
        self.start_date_time = game_local_time
        return

        
        
        
        
        
        
        
        
        
        
        
        
        

        
        










