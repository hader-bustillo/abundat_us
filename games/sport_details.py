"""
This module initializes the Sports object with all the necessary configuration details for a
sport which are defined in the config.json. Some of those attributes would be name of the defense,
name of the offense, number of periods in a game etc.
"""
import logging

logger = logging.getLogger(__name__)


class Sports:
    def __init__(self,sports_config):
        logging.info("Initialising the Sport_details \n")
        for key in sports_config:
            setattr(self, key, sports_config[key])

        self.article_codes_to_remove = self.__remove_article_codes()
        
    def __remove_article_codes(self):
        removal_codes = []
        if self.ties_allowed is False:
            logging.debug("Adding the removal code 90\n")
            removal_codes.append(90)
        if self.shutouts_allowed is False:
            logging.debug("Adding the removal code 100\n")
            removal_codes.append(100)
        return removal_codes
