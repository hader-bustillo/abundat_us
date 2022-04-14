"""
This module as the name suggests inits the Team object with the team names, state they belong to ,
mascott names etc.

Used in the games_filter section and also in the actual article write itself.

"""

import logging
from db import dynamo
from utils import utils

logger = logging.getLogger(__name__)


class Team:
    def __init__(self, team_id, city_possessive=False, team_name_without_city=False):
        self.team_id = team_id
        self.warning_flags = {}
        self.kill_flags = {}
        self.team_dict = self.get_team_data()

        self.city = self.__get_value_for_key('city')
        
        self.team_name = self.__get_team_name('teamName', city_possessive,team_name_without_city)
        self.background_team_picture_ids = self.__get_value_for_key('backgroundTeamPictureIds')
        self.url = self.__get_value_for_key('url')
        self.team_id = self.__get_value_for_key('teamId') 
        self.state = self.__get_value_for_key('state')
        
        self.team_name_acronym = self.__get_team_name('acronymteamName', city_possessive,team_name_without_city)
        self.team_name_official = self.__get_team_name('officialTeamName', city_possessive,team_name_without_city)
        self.team_name_ap = self.__get_team_name('apTeamName',city_possessive,team_name_without_city)
        self.team_name_colloquial = self.__get_team_name('colloquialTeamName',city_possessive,team_name_without_city)
        self.team_name_min = self.__get_team_name('minTeamName',city_possessive,team_name_without_city)
        self.team_name_short = self.__get_team_name('shortTeamName',city_possessive,team_name_without_city)
        self.mascot = self.__get_value_for_key('mascot1')
        self.latitude = self.__get_value_for_key('latitude')
        self.longitude = self.__get_value_for_key('longitude')
        self.color_1_id = self.__get_value_for_key('color1Id')
        self.color_2_id = self.__get_value_for_key('color2Id')
        self.color_3_id = self.__get_value_for_key('color3Id')
        self.mascot_team_picture_id = self.__get_value_for_key('mascotTeamPictureIds')
        self.squad_ids = self.__get_value_for_key('squadIds')
        self.varsity_letter = self.__get_value_for_key('varsityLetter')
        self.level_of_play_id = self.__get_value_for_key('levelOfPlayId')
        self.location_id = self.__get_value_for_key('locationId')
        logging.info("Initialised team data for %s with team id %d", self.team_name_official, self.team_id)

    def get_team_data(self):

        team_dict = dynamo.dynamo_get_item(keys=['teamId'], table_name='RS_AI_SS_TEAMS',
                                              vals=[self.team_id])
        if team_dict is not None and type(team_dict) is dict:
            if len(team_dict.keys()) > 0:
                return team_dict
        else:
            logging.info("Team information is not found for %d", self.team_id)
            return None
    
    def __get_value_for_key(self,key):
        if self.team_dict is None or type(self.team_dict) is not dict:
            return None
        elif key in self.team_dict:
            return self.team_dict[key]
        else:
            self.warning_flags["MISSING_VALUE_FOR_KEY"] = key
            logging.info("Missing information for %s in team id %d", str(key), self.team_id)
            return None

    def __get_team_name(self, key: str, city_poss:bool,no_city:bool):
        team_name = self.__get_value_for_key(key)
        if team_name is None:
            logging.info("Missing team name for  team id %d", self.team_id)
            return
        if self.city is None:
            logging.debug("Missing city information for team id %d", self.team_id)
            return utils.properly_capitalize_team_name(team_name)
        elif ''.join(filter(str.isalnum, self.city.lower())) in ''.join(filter(str.isalnum, team_name.lower())):
            logging.debug("city name found in team name for team id %d", self.team_id)
            return utils.properly_capitalize_team_name(team_name)
        else:
            logging.debug("Append city name to team name for team id %d", self.team_id)
            if city_poss:
                new_name = self.city + "'s" + ' ' + team_name
            elif no_city:
                new_name = team_name
            else:
                new_name = self.city + ' ' + team_name
            return utils.properly_capitalize_team_name(new_name)
