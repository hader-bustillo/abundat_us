"""
This is an important module which does the collection of all the required data and puts it
one place not limited to L2 data,L3_data, game data, sports data, team data etc.

"""
from games import game_details, squad_details, team_details
from games import sport_details as sd
from article import article_data
from random import randint
from utils import utils
from db import dynamo
import json
import logging

logger = logging.getLogger(__name__)


class AllGameData:

    def __init__(self,game_dict:dict, written_article_indices: dict, customer_config):
        logging.info("Initializing All Game Data for %d", game_dict['gameId'])

        self.customer_config = customer_config
        self.general_config = self.customer_config.general_config

        self.sports_article_content = self.customer_config.sports_article_content

        self.game_dict = game_dict

        self.individual_game = self.__get_individual_game()

        self.home_team_data = self.__get_team_data(self.individual_game.home_team_id)
        self.away_team_data = self.__get_team_data(self.individual_game.away_team_id)
        self.squad_data = self.__get_squad_data()
        self.sport_details = self.__get_sport_details()

        self.l2_data = self.__get_l2_data(written_article_indices)
        self.l3_data = self.__get_l3_data()


    def __get_l2_data(self, written_article_indices):
        logging.info("Initializing L2 data for game %d", self.individual_game.game_id)
        if self.sport_details is None:
            logging.info("Sports details are empty for game %d, hence empty L2", self.individual_game.game_id)
            return None
        return article_data.L2Rules(game=self.individual_game, sport_details=self.sport_details,
                                    headlines=self.sports_article_content['headlines'],
                                    l2_bases=self.__filter_content_dynamic_articles(self.sports_article_content['l2_summary_content']),
                                    l2_fillers=self.sports_article_content['l2_filler_content'],
                                    written_article_indices=written_article_indices,
                                    customer_config=self.customer_config)

    def __filter_content_dynamic_articles(self, content):
        if hasattr(self.customer_config, 'content_dynamics') and self.customer_config.content_dynamics == 'low':
            logging.info("%s has dynamic content set to %s", self.customer_config.name,
                            self.customer_config.content_dynamics)
            return list(filter(lambda x: x['content_dynamics'] == self.customer_config.content_dynamics, content))
        else:
            return content

    def __get_l3_data(self):
        logging.info("Initializing L3 data for game %d", self.individual_game.game_id)
        if self.sport_details is None:
            logging.info("Sports details are empty for game %d, hence empty L3", self.individual_game.game_id)
            return None
        l3_sentences = []

        for i in range(0, len(self.individual_game.box_scores)-1):

            l3 = article_data.L3Data(neither_scored=self.sports_article_content['l3_neither_scored'],
                                     game=self.individual_game, period_num=i,
                                     tie=self.sports_article_content['l3_tie'],
                                     winning_losing=self.sports_article_content['l3_winning_losing'],
                                     winning_winning=self.sports_article_content['l3_winning_winning'],
                                     sport_details=self.sport_details,
                                     l3_data_list=l3_sentences,
                                     customer_config=self.customer_config)

            l_final = l3.final_output

            l3_sentences.append(l_final)

        if randint(0,10) % 2 == 0:
            
            if len(l3_sentences) >= 3 and l3.get_key_period_name() in l3_sentences[2]:
                l3_sentences[0]=utils.replace_item_in_string(current=l3.get_key_period_name(),
                                                             in_str=l3_sentences[0],new='period')
            elif len(l3_sentences) >=3 and l3.get_key_period_name() in l3_sentences[len(l3_sentences)-1]:
                l3_sentences[len(l3_sentences)-1]=utils.replace_item_in_string(current=l3.get_key_period_name(),
                                                                               in_str=l3_sentences[len(l3_sentences)-1],
                                                                               new='period')
        else:
            
            if len(l3_sentences) >= 3 and l3.get_key_period_name() in l3_sentences[len(l3_sentences)-1]:
                l3_sentences[len(l3_sentences)-1]=utils.replace_item_in_string(current=l3.get_key_period_name(),
                                                                               in_str=l3_sentences[len(l3_sentences)-1],
                                                                               new='period')
            elif len(l3_sentences) >=3 and l3.get_key_period_name() in l3_sentences[2]:
                l3_sentences[0]=utils.replace_item_in_string(current=l3.get_key_period_name(),
                                                             in_str=l3_sentences[0], new='period')
        logging.info("Completed L3 data for game %d", self.individual_game.game_id)
        return l3_sentences
    
    def __get_individual_game(self):
        logging.info("Initializing Individual game data for game %d", self.game_dict['gameId'])
        return game_details.Game(game_dict=self.game_dict)
    
    def __get_squad_data(self):
        logging.info("Initializing squad data for game %d for squad %d", self.game_dict['gameId'],
                    self.individual_game.home_squad_id)
        return squad_details.Squads(squad_id=self.individual_game.home_squad_id)  # game.game.home_squad_id
        
    def __get_team_data(self,team_id):
        logging.info("Initializing squad data for game %d for team %d", self.game_dict['gameId'], team_id)
        city_possessive = False
        no_city_name = False

        if hasattr(self.customer_config, 'city_possessive'):
            city_possessive = self.customer_config.city_possessive
        if hasattr(self.customer_config, 'no_city_name'):
            no_city_name = self.customer_config.no_city_name
        return team_details.Team(team_id=team_id,city_possessive=city_possessive,team_name_without_city=no_city_name)
    
    def __get_sport_details(self):

        sport_name = self.individual_game.sport_name

        sports_config = list(filter(lambda x: x['sport_name'] == sport_name, self.customer_config.sports_config))

        if sports_config:
            logging.info(" Sport %s is defined in the configuration", sport_name)
            if len(sports_config) > 1:
                sports_config = list(filter(lambda x: x['normal_num_periods'] == len(self.individual_game.box_scores) - 1,
                                            sports_config))[0]
            else:
                sports_config = sports_config[0]

            sport_details = sd.Sports(sports_config=sports_config)

            return sport_details
        else:
            logging.info(" Sport %s is not defined in the configuration", sport_name)
            return None
