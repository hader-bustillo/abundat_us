"""
This initializes the sqaud object with the necessary details as each team can have multiple squad
levels like varsity, junior , middle school etc.

Will be used in the games_filter module as we filter games only for varsity at this point.
"""
import logging
from db import dynamo

logger = logging.getLogger(__name__)


class Squads:
    
    def __init__(self,squad_id):
        self.squad_id = squad_id
        self.warning_flags = {}
        self.kill_flags = {}
        
        self.squad_dict = self.get_squad_data()
    
        self.short_level = self.__get_value_for_key('shortLevel')
        self.scoreboard_display = self.__get_value_for_key('scoreboardDisplay')
        self.display = self.__get_value_for_key('display')
        self.squad_id = self.__get_value_for_key('squadId')
        self.gender = self.__get_value_for_key('gender')
        self.level = self.__get_value_for_key('level')
        self.parent_organization_id = self.__get_value_for_key('parentOrganizationId')
        self.short_display = self.__get_value_for_key('shortDisplay')
        self.gender_level_display = self.__get_value_for_key('selectionDisplay')
        logging.info("Initialised squad data for squad id %d", self.squad_id)

    def get_squad_data(self):
        squad_dict = dynamo.dynamo_get_item(keys=['squadId'], table_name='RS_AI_SS_SQUADS', vals=[self.squad_id])
        if squad_dict is not None and len(squad_dict.keys()) > 0:
            logging.debug("Squad id %d has been found in the db\n", self.squad_id)
            return squad_dict
        else:
            logging.info("Squad id %d is not found in the database\n", self.squad_id)
            return None
    
    def __get_value_for_key(self,key):
        if self.squad_dict is None:
            return None
        elif key in self.squad_dict:
            return self.squad_dict[key]
        else:
            self.warning_flags["MISSING_VALUE_FOR_KEY"] = key
            logging.info("Missing value for %s in squad_dict for squad id %d", str(key), self.squad_id)
            return None
