"""
This module retrieves the content of customer_config.json and constructs a CustomerConfig
object with the appropriate attributes.
"""
import json
import logging
from db import dynamo

logger = logging.getLogger(__name__)


class CustomerConfig:
    def __init__(self, customer_name:str, general_config):
        self.general_config = general_config
        self.sports_article_content = self._get_sports_article_content()
        customer_config = self._read_customer_configuration(customer_name)
        if customer_config:
            for key in customer_config:
                setattr(self, key, customer_config[key])
            self.coverage_team_list = []
            self.coverage_squad_list = []
            self._convert_sports_interested()
        else:
            raise ValueError

    def _read_customer_configuration(self, customer_name):
        try:
            customer_config_table = self.general_config['customer_config_table']

            customer_config = dynamo.dynamo_get_item(table_name=customer_config_table, keys=['name'],
                                                     vals=[customer_name])
            logging.info("found the customer config %s", repr(customer_config))
        except Exception as e:
            logging.info("Customer %s not found", customer_name)
            customer_config = None
        return customer_config

    def _convert_sports_interested(self):
        sports_config_table = self.general_config['sports_config']

        logging.info("fetching all the entries from the sports config table")

        sports_config = dynamo.dynamo_db_scan(table_name=sports_config_table)

        self.sports_config = sports_config

        for each_item in self.sports_interested:
            if each_item == 'all':

                logging.info("converting all to list of sports")

                self.sports_interested = list(set([x['sport_name'] for x in self.sports_config]))

                break

        logging.info("the customers interested sports are %s", self.sports_interested)

    def get_list_of_teams_by_sport(self, team_list):
        sport_team_list = {}
        if self.coverage is not None:
            for item in self.coverage:
                filtered_team_list = self._get_team_list(item, team_list)
                if 'sport' in item and filtered_team_list:
                    if type(item['sport']) is list:
                        for sport_name in item['sport']:
                            sport_team_list[sport_name] = filtered_team_list
                    else:
                        sport_team_list[item['sport']] = filtered_team_list
            return sport_team_list
        else:
            logging.info("Customer Configuration is None\n")

    def get_list_of_squads_by_sport(self):
        sport_squad_list = {}
        if self.coverage is not None:
            for item in self.coverage:
                squad_list = self.get_squad_list(item)
                if 'sports_level' in item and squad_list:
                    if type(item['sport']) is list:
                        for sport_name in item['sport']:
                            sport_squad_list[sport_name] = squad_list
                    else:
                        sport_squad_list[item['sport']] = squad_list
            return sport_squad_list

    def _get_team_list(self, item, teams_list):
        team_list = {'teams': [], 'exclude_teams': []}

        if 'definition' in item:
            if item['definition'] == 'state':
                for state in item['id_lists']:
                    team_list['teams'] += self._get_teams_by_state(state, teams_list)
            elif item['definition'] == 'school':
                team_list['teams'] += item['id_lists']
            elif item['definition'] == 'cities':
                team_list['teams'] += self._get_teams_by_city(item['id_lists'], teams_list)
            elif item['definition'] == 'exclude_cities':
                team_list['exclude_teams'] += self._get_teams_by_city(item['city_list'], teams_list)
                for state in item['state_list']:
                    team_list['teams'] += self._get_teams_by_excluding_city(state=state, city_list=item['city_list'], team_list=teams_list)
        return team_list

    @staticmethod
    def _get_teams_by_excluding_city(state, city_list, team_list):

        team_id_list = [team['teamId'] for team in team_list if team['city'] + ',' + team['state'] not in city_list and team['state'] == state]

        return team_id_list

    @staticmethod
    def _get_teams_by_state(state, team_list):
        teamid_list = [team['teamId'] for team in team_list if team['state'] == state]
        return teamid_list

    @staticmethod
    def _get_teams_by_city(citylist: list, team_list):

        teamid_list = [team['teamId'] for team in team_list if team['city'] + ',' + team['state'] in citylist]

        logging.info("The number of teams filtered for the city are %d",len(teamid_list))
        return teamid_list

    @staticmethod
    def get_squad_list(item):
        squad_list = item['sports_level'] if 'sports_level' in item else []
        return squad_list

    def _get_sports_article_content(self):
        article_keys_to_get = ["headlines", "l2_summary_content", "l3_tie", "l3_winning_losing",
                                "l3_neither_scored", "l2_filler_content", "l3_winning_winning", "deep_link", 
                                "deep_link_end_fillers"]
        article_content = {}
        for each_key in article_keys_to_get:
            content = dynamo.dynamo_get_item(table_name=self.general_config['article_content_table'], keys=['content_type'],
                                                vals=[each_key])

            article_content[each_key] = content['content']
        return article_content
