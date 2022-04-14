import json
from db import dynamo
import logging
import datetime
from utils import utils
from games import agd
import re
from article.article_data import L2Data
from boto3.dynamodb.conditions import Key, Attr
from copy import deepcopy


# get the team ids and query the database for any possible matches
# if there was a match

logger = logging.getLogger(__name__)


class DeepLink:
    def __init__(self, game, sports_config, customer_config):
        self.game = game
        self.sports_config = sports_config
        self.customer_config = customer_config
        self.date_time = self.game.start_date_time
        self.general_config = self.customer_config.general_config
        self.sports_article_content = self.customer_config.sports_article_content
        self.customer_system_name = self._get_customer_system_name()
        self.ddb_id = self.__get_ddb_id(alt=False)
        self.ddb_alt_id = self.__get_ddb_id(alt=True)

        self.yearly_article = self._get_yearly_round_up()
        self.weekly_articles = self._get_weekly_round_up()

    def _get_customer_system_name(self):
        active_publishing_system = [system for system in self.customer_config.publishing_system if system['active']]
        if active_publishing_system:
            return active_publishing_system[0]['system_name']
        else:
            return 'UNKNOWN'

    def __get_ddb_id(self, alt: bool):

        if alt:
            ddb_id = self.customer_config.name + '_' + \
                        str(self.game.away_team_id) + '_' + \
                        str(self.game.home_squad_id) + '_' \
                        + self.game.sport_name.lower() + '_' + self.customer_system_name
        else:
            ddb_id = self.customer_config.name + '_' + \
                        str(self.game.home_team_id) + '_' + \
                        str(self.game.home_squad_id) + '_' \
                        + self.game.sport_name.lower() + '_' + self.customer_system_name
        return ddb_id

    def __filter_based_on_article_lang(self, article):
        article_language = 'en'
        if hasattr(self.customer_config, 'article_language') and self.customer_config.article_language and 'content' in article and type(article['content']) is dict and self.customer_config.article_language in article['content']:
            article_language = self.customer_config.article_language
        article['content'] = deepcopy(article['content'][article_language])
        return article

    def _scan_weekly_posted_assets_table(self):

        min_date = (self.date_time - datetime.timedelta(days=self.sports_config.num_of_days_weekly_max)).strftime('%Y-%m-%d')
        max_date = (self.date_time - datetime.timedelta(days=self.sports_config.num_of_days_weekly_min)).strftime('%Y-%m-%d')

        home_team_scan = self._get_items_from_posted_tables(min_date=min_date,max_date=max_date,
                                                            home_team=True)
        if home_team_scan:
            home_team_scan = [sorted(home_team_scan, key=lambda x: x['game_start_time'], reverse=True)[0]]

        away_team_scan = self._get_items_from_posted_tables(min_date=min_date, max_date=max_date,
                                                            home_team=False)
        if away_team_scan:
            away_team_scan = [sorted(away_team_scan, key=lambda x: x['game_start_time'], reverse=True)[0]]

        team_scan = home_team_scan + away_team_scan

        return team_scan

    def _get_items_from_posted_tables(self, min_date, max_date, home_team):

        if home_team:
            ddb_key = self.ddb_id
        else:
            ddb_key = self.ddb_alt_id

        items1 = self._query_from_asset_table(table_name=self.general_config['posted_assets_table'],
                                              min_date=min_date,
                                              max_date=max_date,
                                              key=ddb_key,
                                              system_name=self.customer_system_name)
        items2 = self._get_item_using_alt_id(min_date,max_date, ddb_key)

        combined_items = items1 + items2

        return combined_items

    def _get_item_using_alt_id(self,min_date,max_date, ddb_key):
        items = self._query_from_asset_table(table_name=self.general_config['posted_assets_table_alt'],
                                             min_date=min_date,
                                             max_date=max_date,
                                             key=ddb_key,
                                             system_name=self.customer_system_name)
        alt_items = []
        for each_item in items:
            alt_items.append(dynamo.dynamo_get_item(table_name=self.general_config['posted_assets_table'],
                                                    keys=['id', 'game_start_time'], vals=[each_item['alt_id'],
                                                                                          each_item['game_start_time']]))
        return alt_items

    @staticmethod
    def _query_from_asset_table(table_name, min_date, max_date, key, system_name):

        items = dynamo.dynamo_query_table_with_filter(table_name=table_name,
                                                      keycondition_expression=Key('id').eq(key) &
                                                                              Key('game_start_time').between(min_date,max_date))

        return items

    def _scan_yearly_posted_assets_table(self):
        min_date = (self.date_time - datetime.timedelta(days=self.sports_config.num_of_days_yearly_max)).strftime('%Y-%m-%d')
        max_date = (self.date_time - datetime.timedelta(days=self.sports_config.num_of_days_yearly_min)).strftime('%Y-%m-%d')

        home_team_scan = self._get_items_from_posted_tables(min_date=min_date,max_date=max_date,
                                                            home_team=True)

        if home_team_scan:
            home_team_scan = [item for item in home_team_scan if (item['away_team_id'] == self.game.away_team_id) or (item['home_team_id'] == self.game.away_team_id)]
            if home_team_scan:
                home_team_scan = sorted(home_team_scan, key=lambda x: x['game_start_time'], reverse=True)[0]

        logging.info("the items found in the yearly scan in deep linking are %s", repr(home_team_scan))
        return home_team_scan

    def _get_yearly_round_up(self):
        return_dict = {'txt': '', 'html': ''}
        yearly_data = self._scan_yearly_posted_assets_table()

        if yearly_data:
            return self._get_yearly_article(yearly_data)
        else:
            logging.info("no yearly data found for game %s ", repr(self.game.game_id))
            return return_dict

    def _get_weekly_round_up(self):
        return_dict = {'txt': '', 'html': ''}

        weekly_data_list = self._scan_weekly_posted_assets_table()

        if weekly_data_list:
            logging.info("Weekly data found for game %s as %s", repr(self.game.game_id), repr(weekly_data_list))
            return self._get_weekly_articles(weekly_data=weekly_data_list)
        else:
            logging.info("no weekly data found for game %s ", repr(self.game.game_id))
            return return_dict

    def _get_weekly_articles(self, weekly_data:list):

        deep_link_articles = self.sports_article_content['deep_link']

        weekly_articles = []

        if len(weekly_data) == 1:
            weekly_articles = list(filter(lambda x: x['category'] == 'weekly' and x['type'] == 'one_team', deep_link_articles))
        elif len(weekly_data) == 2:
            weekly_articles = list(filter(lambda x: x['category'] == 'weekly' and x['type'] == 'both_teams', deep_link_articles))

        rand_num = utils.get_random_int(len(weekly_articles)-1)

        selected_article = deepcopy(weekly_articles[rand_num])

        selected_article = self.__filter_based_on_article_lang(selected_article)

        agd1 = self._get_all_game_data(game_id=weekly_data[0]['game_id'], home_team_id=weekly_data[0]['home_team_id'])

        if agd1.determine_winning_team()[0].team_id == self.game.away_team_id or \
                agd1.determine_winning_team()[0].team_id == self.game.home_team_id:
            agd1_is_winning = True
        else:
            agd1_is_winning = False

        agd2 = None
        agd2_is_winning = None

        if len(weekly_data) > 1:
            agd2 = self._get_all_game_data(game_id=weekly_data[1]['game_id'],
                                           home_team_id=weekly_data[1]['home_team_id'])

            if agd2.determine_winning_team()[0].team_id == self.game.away_team_id or \
                    agd2.determine_winning_team()[0].team_id == self.game.home_team_id:
                agd2_is_winning = True
            else:
                agd2_is_winning = False

        replaced_article = self._construct_replacement_data(agd1=agd1, agd2=agd2, article=selected_article,
                                                            agd1_is_winning=agd1_is_winning, agd2_is_winning=agd2_is_winning)

        article_html_txt = self._construct_html_txt(original_article=replaced_article, data=weekly_data)

        logging.info("the weekly replaced article is %s ", repr(article_html_txt))
        return article_html_txt

    def _get_yearly_article(self, yearly_data):

        deep_link_articles = self.sports_article_content['deep_link']

        yearly_articles = list(filter(lambda x : x['category'] == 'yearly', deep_link_articles))

        rand_num = utils.get_random_int(len(yearly_articles)-1)

        selected_article = deepcopy(yearly_articles[rand_num])

        selected_article = self.__filter_based_on_article_lang(selected_article)

        agd1 = self._get_all_game_data(game_id=yearly_data['game_id'], home_team_id=yearly_data['home_team_id'])

        if agd1.determine_winning_team()[0].team_id == self.game.away_team_id or \
                agd1.determine_winning_team()[0].team_id == self.game.home_team_id:
            agd1_is_winning = True
        else:
            agd1_is_winning = False

        replaced_article = self._construct_replacement_data(agd1=agd1, article=selected_article,
                                                            agd1_is_winning=agd1_is_winning)

        article_html_txt = self._construct_html_txt(original_article=replaced_article, data=yearly_data)

        logging.info("the yearly replaced article is %s ", repr(article_html_txt))

        return article_html_txt

    @staticmethod
    def _construct_html_txt(original_article, data):
        article = {}
        if type(data) is dict:
            article['html'] = "<p>" + "<a href=\"" + data['post_url'] + "\">" + original_article + "</a></p>"
            article['txt'] = original_article + "[\"" + data['post_url'] + "\"]\n"
        elif type(data) is list:
            article['html'] = "<p>"
            article['txt'] = ""
            original_article_array = original_article.split('[[SENTENCE_CONJUNCTION]]')
            for index, (each_data, each_article) in enumerate(zip(data, original_article_array)):
                if index > 0:
                    article['html'] += "and"
                    article['txt'] += "and"
                article['html'] += "<a href=\"" + each_data['post_url'] + "\">" + each_article + "</a>"
                article['txt'] += each_article + "[\"" + each_data['post_url'] + "\"]"
            article['html'] += "</p>"
            article['txt'] += "\n"
        return article

    def _scan_games_table(self, game_id, home_team_id):
        game_dict = dynamo.dynamo_get_item(table_name='RS_AI_SS_GAMES',
                                           keys=['gameId', 'homeTeamId'], vals=[game_id, home_team_id])
        return game_dict

    def _get_all_game_data(self, game_id, home_team_id):
        game_dict = self._scan_games_table(game_id=game_id, home_team_id=home_team_id)

        all_data = agd.AllGameData(game_dict=game_dict, written_article_indices={},
                                   customer_config=self.customer_config)
        
        
        apa_format_month = utils.get_apa_format_month(self.customer_config)

        ad = L2Data(squad_data=all_data.squad_data, away_team_data=all_data.away_team_data,
                    lead=all_data.l2_data.lead, game=all_data.individual_game,
                    home_team_data=all_data.home_team_data, all_game_data=all_data,
                    apa_format_month=apa_format_month)
        return ad


    def _construct_replacement_data(self, article, agd1, agd1_is_winning, agd2=None, agd2_is_winning=None):

        deep_link_fillers = self.sports_article_content['deep_link_end_fillers']

        rand_int = utils.get_random_int(20) % len(deep_link_fillers)

        filler_sentence = deepcopy(deep_link_fillers[rand_int])

        filler_sentence = self.__filter_based_on_article_lang(filler_sentence)['content']

        replacement_dict1 = {
            '[[TEAM_A_GAME_SCORE]]': agd1.base_score_string,
            '[[TEAM_A_GAME_LOCATION]]':agd1.site_name,
            '[[TEAM_A_NAME]]': agd1.winning_team_name if agd1_is_winning else agd1.losing_team_name,
            '[[TEAM_A_OPPONENT]]': agd1.losing_team_name if agd1_is_winning else agd1.winning_team_name,
            '[[TEAM_A_GAME_DATE_YEAR]]': agd1.game.start_date_time.strftime("%B %-d, %Y"),
            '[[TEAM_A_GAME_DATE]]': agd1.game_played_date,
            '[[SPORT]]': agd1.all_game_data.individual_game.sport_name.lower(),
            '[[ARTICLE_FILLERS]]': filler_sentence
        }

        replaced_article = self._replace_regex_items(article=article['content'], replacement_dict=replacement_dict1)

        if agd2:
            replacement_dict2 = {
                '[[TEAM_B_GAME_SCORE]]': agd2.base_score_string,
                '[[TEAM_B_GAME_LOCATION]]': agd2.site_name,
                '[[TEAM_B_NAME]]': agd2.winning_team_name if agd2_is_winning else agd2.losing_team_name,
                '[[TEAM_B_OPPONENT]]': agd2.losing_team_name if agd2_is_winning else agd2.winning_team_name,
                '[[TEAM_B_GAME_DATE]]': agd2.game_played_date
            }
            replaced_article = self._replace_regex_items(article=replaced_article, replacement_dict=replacement_dict2)
        return replaced_article

    def _replace_regex_items(self, article, replacement_dict):
        rep = dict((re.escape(k), v) for k, v in replacement_dict.items())
        pattern = re.compile("|".join(rep.keys()))
        article = pattern.sub(lambda m: rep[re.escape(m.group(0))], article)
        return article

