"""
This module contains 3 major classes namely L2Rules, L2Data and L3Data and one minor class
RsSportsArticleComponents.

RsSportsArticleComponents - class representing the headline/article data content structure
of the articles present in the article_content.json

L2Rules - determines the article code and the type of the game. Checks for various conditions
          to arrive at the right type of scenario and gets a base lead sentence.
L2Data - populates all the required supplemnetary data necessary for the L2Rules.
L3Data - Determines the articles to be written for each period of the game analyzing the score
         in the particular period and the way it affects the entire state of the game.
"""

from utils import utils
from games import game_details
from games import sport_details as sd
from article import article_speech_parts
import logging
import random
from collections import deque
from copy import deepcopy


logger = logging.getLogger(__name__)


class RsSportsArticleComponents:
    def __init__(self, dict_content: dict):
        
        self.dict_content = dict_content
        self.content = self.dict_content['content']
        self.content_type = self.dict_content['content_type']
        self.content_code = self.dict_content['content_code']
        self.content_code_name = self.dict_content['content_code_name']
        self.content_scoring_type = self.dict_content['content_scoring_type']
        self.date_added = self.dict_content['date_added']
        self.content_dynamics = self.dict_content['content_dynamics'] if 'content_dynamics' in dict_content else None
        

class L2Rules:
    
    def __init__(self,
                 sport_details: sd.Sports,
                 game: game_details.Game,
                 headlines: list,
                 l2_bases:list,
                 l2_fillers:list,
                 written_article_indices: dict,
                 customer_config):

        logging.info("Initialising the L2 Rules\n")
        self.kill_flags = {}
        self.warning_flags = {}
        
        self.sport_details = sport_details
        self.game = game
        self.headlines = self.convert_content(headlines)
        self.l2_bases = self.convert_content(l2_bases)
        self.l2_fillers = self.convert_content(l2_fillers)
        self.written_article_indexes = written_article_indices
        self.customer_config = customer_config
        
        '''
        Score early hold on means the winning team scored >= number of points necessary and margin, and won in end by <= margin
        Score early pull away means winning team met score early criteria and won by >= margin
        Trail early means they were losing by a key margin after the num_periods and won
        '''
        self.article_content_dynamics = None

        self.article_code = self.get_l2_article_code()
        
        self.headline = self.__get_headline()

        self.lead_base = self.__get_lead_base()
        
        self.lead_filler = self.__get_lead_filler()
        
        self.lead = self.__get_complete_lead()


    def __get_headline(self):
        from random import randint
        code = self.article_code
           
        if code not in [100, 90, 70, 40, 80, 50, 60, 30, 20, 10]:

            for i in [self.get_big_win_code(), self.get_competitive_win_code(), self.get_close_win_code()]:
                if i is not None:
                    code = i
                    break
            if i is None:
                if self.game.sport_name != 'soccer':
                    code = 50
                else:
                    code = 60
        logging.info("The code for this article is selected to be %d\n", code)
        try:
            article_headline = self.__select_article(article_code=self.article_code, content=self.headlines).content
        except (AttributeError, IndexError):
            logging.info("Appending a generic headline\n")
            article_headline = '[[WINNING_TEAM]] beats [[LOSING_TEAM]]'
        return article_headline

    def __get_lead_base(self):
        article = self.__select_article(article_code=self.article_code,
                                                             content=self.l2_bases,
                                                             exclude=self.sport_details.exclude_terms)
        self.article_content_dynamics = article.content_dynamics

        return utils.add_period_to_end(article.content)

    def __get_lead_filler(self):
        return self.change_content_based_on_double_word()
    
    def __get_complete_lead(self):
        from utils import utils
        lb = self.lead_base
        lb = utils.replace_item_in_string(current='[[FILLER]]', in_str=lb,new=self.lead_filler)
        return utils.add_period_to_end(lb)+'\n'

    def __select_article(self, article_code, content, exclude=[]):
        if article_code is not None:
            select_articles = self._filter_articles(articles=content, article_code=article_code,
                                                    exclude=exclude)
        else:
            select_articles = content

        article = random.choice(select_articles)
        
        self._update_written_article_indexes(articles=content, article_code=article_code,
                                             article=article)
        
        article = deepcopy(article)

        article_language = 'en'
        if hasattr(self.customer_config, 'article_language') and self.customer_config.article_language and type(article.content) is dict and self.customer_config.article_language in article.content:
            article_language = self.customer_config.article_language
        article.content = article.content[article_language]
        return article

    def _update_written_article_indexes(self, articles, article_code, article):
        list_max_range = int(len(list(filter(lambda template: template.content_scoring_type == 'any' and
                                             template.content_code == article_code,
                                             articles))) / 2)
        # Get the index of the article selected

        content_index = articles.index(article)

        article_code_content_type = articles[0].content_type + '_' + str(article_code)

        index_queue = deque(self.written_article_indexes[article_code_content_type])
        index_queue.append(content_index)

        if len(index_queue) > list_max_range:
            index_queue.popleft()
        self.written_article_indexes[article_code_content_type] = list(index_queue)
        logging.info("The stored written indexes for %s are %s", article_code_content_type,
                    repr(self.written_article_indexes))

    def _filter_articles(self, articles, article_code, exclude=[]):
        # Get the type of content along with the article code

        selected_articles = articles
        article_code_content_type = articles[0].content_type + '_' + str(article_code)

        # Filter the articles based on the article code, scoring type and exclude filter

        selected_articles = list(filter(lambda article: article.content_scoring_type == 'any' and
                                        article.content_code == article_code, selected_articles))
        # Exclude filter - the words that are not applicable for the sports
        if exclude:
            selected_articles = [article for article in selected_articles
                                 for word in exclude if word not in article.content]

        if article_code_content_type not in self.written_article_indexes:
            self.written_article_indexes[article_code_content_type] = []
        else:
            filtered_articles = [article for index,article in enumerate(selected_articles)
                                 if index not in self.written_article_indexes[article_code_content_type]]
            if filtered_articles:
                selected_articles = filtered_articles

        return selected_articles

    def change_content_based_on_double_word(self):
        words = [' in ', ' for ', ' victory ', ' during ']
        exclude_terms = list(filter(lambda x: x in self.lead_base, words))
        filler_text = self.__select_article(article_code=1010,
                                            content=self.l2_fillers, exclude=exclude_terms).content
        logging.debug("The filler text is found to be %s", filler_text)
        return filler_text

    #RIGHT NOW ONLY 'ANY' SCORING ARTICLES ARE WRITTNE
    def convert_content(self,content:list):
        standard_arr = []
    
        for article in content:
            if 'content_scoring_type' not in article:
                article['content_scoring_type'] = 'any'
            if 'date_added' not in article:
                article['date_added'] = None
            article_data = RsSportsArticleComponents(dict_content=article)
            standard_arr.append(article_data)

        return standard_arr
    
    def get_score_for_period(self, winning: bool):
        key = ''
        score = 0
        if winning is True:
            if self.game.home_team_won is True:
                key = 'homeTeamScore'
            else:
                key = 'awayTeamScore'
        if winning is False:
            if self.game.home_team_won is True:
                key = 'awayTeamScore'
            else:
                key = 'homeTeamScore'
        
        for i in range(0, self.sport_details.num_periods_for_early):
            if key in self.game.box_scores[i]:
                score = score + self.game.box_scores[i][key]
            logging.info("the %s score is %d for period %d", key, score, i)
        return score

    def __get_score_early_pull_away_code(self):
        from utils import utils
        winning_score = self.get_score_for_period(True)
        losing_score = self.get_score_for_period(False)
        
        random_int = utils.get_random_int(20)
        
        # Added random integer because we have fewer score_early_pull_away than competive/big win codes, so 20%
        #  (in theory) should receive general win codes instead
        
        if winning_score >= self.sport_details.score_early_team_min and winning_score-losing_score >=\
                self.sport_details.score_early_margin_min:
            if abs(self.game.home_team_score - self.game.away_team_score) >= \
                    self.sport_details.score_early_margin_min and random_int % 2 != 0:
                logging.info("Its a score early pull away game\n")
                return True

    def __get_score_early_hold_on_code(self):
        winning_score = self.get_score_for_period(True)
        losing_score = self.get_score_for_period(False)
        
        if winning_score >= self.sport_details.score_early_team_min and winning_score-losing_score >= \
                self.sport_details.score_early_margin_min:
            if abs(self.game.home_team_score - self.game.away_team_score) < self.sport_details.score_early_margin_min:
                logging.info("Its a score early hold on game\n")
                return True
    
    def __get_trail_early_and_rally_code(self):
            winning_score = self.get_score_for_period(True)
            losing_score = self.get_score_for_period(False)
            if winning_score < losing_score and abs(self.game.home_team_score - self.game.away_team_score) >= \
                    self.sport_details.trail_early_margin_min:

                logging.info("Its a trail early and rally\n")
                return True
    
    def get_big_win_code(self):
        if abs(self.game.home_team_score - self.game.away_team_score) >= self.sport_details.big_win_min:
            logging.info("Its a big win\n")
            return True
    
    def get_competitive_win_code(self):
        if abs(self.game.home_team_score - self.game.away_team_score) >= self.sport_details.competitive_win_min:
            logging.info("Its a competitive win\n")
            return True
    
    def get_close_win_code(self):
        if 0 < abs(self.game.home_team_score - self.game.away_team_score) <= self.sport_details.close_win_max:
            logging.info("Its a close win\n")
            return True
        
    def __get_overtime_code(self):
        num_periods = len(self.game.box_scores)
        valid = False
        # The last box score is always the final score , hence you would always boc scores length 1
        # greater than the period length
        if num_periods > self.sport_details.normal_num_periods + 1:
            for ot_period in range(self.sport_details.normal_num_periods, num_periods - 1):
                if self.game.box_scores[ot_period]['homeTeamScore'] > 0 or \
                   self.game.box_scores[ot_period]['awayTeamScore'] > 0:
                    valid = True
                    break
        return valid

    def __get_tie_code(self):
        if self.game.home_team_score == self.game.away_team_score:
            logging.info("Its a tie game\n")
            return True

    def __get_shutout_win_code(self):
        if self.game.home_team_score == 0 or self.game.away_team_score == 0:
            logging.info("Its a shutout win\n")
            return True
        
    def __get_game_stoppage_code(self):
        if self.game.stoppage_status_id is not None and self.game.stoppage_status_id != 9999:
            return True
        
    def get_l2_article_code(self):
        ties_allowed = ['soccer', 'hockey']

        if self.__get_game_stoppage_code():
            return 110
        elif self.__get_overtime_code():
            num_periods = len(self.game.box_scores)
            if num_periods == self.sport_details.normal_num_periods+2:
                logging.info("Number of periods exceeded by 2\n")
                return 70
            elif num_periods > self.sport_details.normal_num_periods+2:
                logging.info("Number of periods exceeded by 3\n")
                return 80
        elif self.__get_tie_code() and self.game.sport_name in ties_allowed:
            return 90
        elif self.__get_shutout_win_code():
            return 100
        elif self.__get_score_early_pull_away_code():
            return 10
        elif self.__get_score_early_hold_on_code():
            return 20
        elif self.__get_trail_early_and_rally_code():
            return 30
        elif self.get_big_win_code():
            return 40
        elif self.get_competitive_win_code():
            return 50
        elif self.get_close_win_code():
            return 60
        elif self.game.sport_name in ties_allowed:
            return 50
        else:
            return 60


class L3Data:
    
    '''
    period_num is the index in current_box, so it is quarter number - 1
    '''
    
    def __init__(self, game, sport_details: sd.Sports,
                 period_num,
                 neither_scored: list,
                 winning_winning: list,
                 winning_losing: list,
                 tie: list,
                 l3_data_list: list,
                 customer_config):

        self.sport_details = sport_details
        self.period_num = period_num
        self.period_num_list = [period_num]
        self.winning_winning = winning_winning
        self.winning_losing = winning_losing
        self.neither_scored = neither_scored
        self.customer_config = customer_config
        self.tie = tie
        self.game = game
        self.l3_data_list = l3_data_list
        self.is_final_period = self.__is_final_period()
        
        self.current_box = self.__get_current_box()
        
        self.home_score_overall = self.get_score_for_period(home=True,period=period_num)
        self.away_score_overall = self.get_score_for_period(home=False,period=period_num)
        
        self.home_score_in_period = self.get_score_in_period(True)
        self.away_score_in_period = self.get_score_in_period(False)

        self.key_period_name = self.get_key_period_name()

        self.score = self.__determine_score()
        self.score_in_period = self.__get_score_string_in_period()
        
        self.base_sentence_type = ''
        self.base_sentence = ''
        self.general_scenario = ''
        self.primary_time = self.get_primary_time()

        self.sentence = self.get_l3_output_sentence()
        
        self.final_output = self.__get_final_output()

    def __is_final_period(self):
        if self.period_num == self.sport_details.normal_num_periods-1 and \
                len(self.game.box_scores) == self.sport_details.normal_num_periods + 1:
                logging.info("Its a final period\n")
                return True
        elif len(self.game.box_scores) > self.sport_details.normal_num_periods+1 and \
                self.period_num+2 > self.sport_details.normal_num_periods:
            logging.info("Its a final period\n")
            #in overtime - all overtime periods work as same
            return True
        else:
            return False

    def __get_current_box(self):
        return self.game.box_scores[self.period_num]

    def get_score_for_period(self, home:bool, period=int):
        score = 0
        key = ''
        if home is True:
            key = 'homeTeamScore'
        elif home is False:
            key = 'awayTeamScore'
    
        if key in self.current_box and period == 0:
            return self.current_box[key]
        elif period > 0 and period < len(self.game.box_scores): 
            for i in range(0, period+1):
                if key in self.game.box_scores[i]:
                    if self.game.box_scores[i][key] < 0:
                        return 9999
                    score = self.game.box_scores[i][key] + score
                else:
                    return 9999
            logging.info("The %s overall score for the period %d is %d", key, period, score)
            return score
        else:
            return 9999
        
    def get_score_in_period(self, home: bool):
        if home is True:
            key = 'homeTeamScore'
        else:
            key = 'awayTeamScore'
        
        if key in self.current_box:
            logging.info("The %s score for the period %d is %d", key, self.period_num, self.current_box[key])
            return self.current_box[key]

        else:
            return 9999
    
    def __get_score_string_in_period(self):
        return self.__ret_score_string(home_score=self.home_score_in_period,away_score=self.away_score_in_period)
    
    def __determine_score(self):
        if self.is_final_period is True:
            return self.__ret_score_string(self.home_score_overall,self.away_score_overall)
        else:
            return self.__ret_score_string(home_score=self.home_score_overall,away_score=self.away_score_overall)
    
    def __ret_score_string(self,home_score:int,away_score:int):
        
        if self.home_score_overall == 9999 or self.away_score_overall == 9999:
            logging.info("one of the scores found to be 9999\n")
            return 9999
        elif home_score >= away_score:
            logging.info("Home score is greater than or equal to away score%d-%d", home_score, away_score)
            return '%i-%i' % (home_score, away_score)
        elif home_score < away_score:
            logging.info("Away score is greater than Home score%d-%d", away_score, home_score)
            return '%i-%i' % (away_score,home_score)
        else:
            logging.info("Returning a 9999\n")
            return 9999

    def __check_for_lead_change(self, winning_team_winning:bool):
        #if, in the previous box, the team that was winning is now not winning, return True
        if self.period_num > 0:
            home_score_previous = self.get_score_for_period(home=True,period=self.period_num-1)
            away_score_previous = self.get_score_for_period(home=False,period=self.period_num-1)
            
            if (self.home_score_overall > self.away_score_overall and home_score_previous > away_score_previous) or \
                (self.away_score_overall > self.home_score_overall and away_score_previous > home_score_previous):
                logging.info("No Score lead changed in the current period\n")
                return False
            else:
                logging.info("Score lead changed in the current period\n")
                return True
        else:
            return False

    def __check_for_kept_margin(self, winning_team_winning:bool):
        #if, in the previous box, the team that was winning is still winning, return True
        if self.period_num > 0:
            if winning_team_winning is True and self.game.winning_score_key > self.game.losing_score_key:
                logging.info("Winning margin is kept by the team\n")
                return True
            elif winning_team_winning is False and self.game.winning_score_key < self.game.losing_score_key:
                logging.info("Winning margin is kept by the team\n")
                return True
        else:
            logging.info("Winning margin is not kept by the team\n")
            return False
        
    def check_for_neither_scored(self):
        if self.home_score_in_period == 0 and self.away_score_in_period == 0:
            logging.info("Neither team scored in the period\n")
            return True
        else:
            return False
        
    def get_base_sentence_type(self,winning_team_winning:bool):
        #if there's a lead change return 'lead_change', if kept_margin return 'kept_margin', else return 'general'
        if self.__check_for_lead_change(winning_team_winning) is True:
            return 'lead_change'
        elif self.__check_for_kept_margin(winning_team_winning) is True:
            return 'kept_margin'
        else:
            return 'general'

    def __check_for_start_(self):
        if self.period_num == 0:
            return True
        else:
            return False
         
    def __check_for_end(self):
        # if the period_num == len(sport_details.number_normal_periods)-1 return True
        if self.period_num == int(self.sport_details.normal_num_periods)-1 and \
                len(self.game.box_scores) == self.sport_details.normal_num_periods+1:
            logging.info("Its the end of the game\n")
            return True
        else:
            return False

    def __check_for_half(self):
        #if period_num == int(sport_details.number_normal_periods/2) return True
        if self.period_num == int(self.sport_details.normal_num_periods/2)-1 and self.key_period_name != 'inning':
            logging.info("Its half time\n")
            return True
        else:
            return False

    def get_primary_time(self):
        # if check for start is True: return 'start', check for end return 'end', check for half return 'half',
        #  else return 'any'
        if self.__check_for_start_() is True:
            return 'start'
        elif self.__check_for_half() is True:
            return 'half'
        elif self.__check_for_end() is True:
            return 'end'
        else:
            return 'any'

    def get_filler_period_num(self,filler_beginning:bool):

        add_int = 0
        if filler_beginning is False:
            add_int = 1
        elif filler_beginning is True:
            add_int = 2
        
        if self.is_final_period is True:
            if len(self.game.box_scores) > self.sport_details.normal_num_periods+1 and self.period_num+1 > \
                    self.sport_details.normal_num_periods:
                return '%s overtime'%utils.number_dict[self.period_num + 1 - self.sport_details.normal_num_periods]
            else:
                return self.get_period_number(self.period_num_list, add_int)
        else:
            return self.get_period_number(self.period_num_list, add_int)

    def get_period_number(self, period_list:list, add_int:int):

        period_num_string_list = [self.get_number_dict_or_final(x=period_num, add_int=add_int) for period_num in period_list]

        period_string = ','.join(period_num_string_list)

        index = period_string.rfind(",")

        if index > 0:
            period_string = period_string[:index] + ' and ' + period_string[index + 1:]

        return period_string

    def get_number_dict_or_final(self, x, add_int):
        rand = utils.get_random_int(10) % 2 == 0
        if rand is True and x == self.sport_details.normal_num_periods - 1:
            return 'final'
        else:
            return utils.number_dict[x+add_int]

    def get_key_period_name(self):
        if '-' in self.game.game_segment_type:
            return self.game.game_segment_type[:-2]
        else:
            return self.game.game_segment_type

    def final_period_filter(self,l:list,content_list:str):
        self.general_scenario = content_list
        choice_arr = []
        score_diff_overall = abs(self.game.home_team_score - self.game.away_team_score)
        '''
        if netiher team scored, add everything from l3_neither_scored with primary_time = 'end'
        if they tied, add everything from l3_tie with primary_time = 'end'
        if winning team extended margin l3_winning_winning and type = 'kept_margin'
        if winning team was losing l3_winning_winning and type = 'lead change'
        
        FOR RIGHT NOW: if winning team was winning l3_winning_winning, all goes to 1 output and upload error to db.
        if winning team was winning l3_winning_winning and type = 'held on'
        
        '''
        
        if content_list != 'winning_winning':
            return 'lead_change'
        else:
            if score_diff_overall <= self.sport_details.competitive_win_min:
                if (self.game.home_team_won is True and self.away_score_in_period <= self.home_score_in_period) or \
                   (self.game.home_team_won is False and self.away_score_in_period >= self.home_score_in_period):
                    return 'kept_margin'
                elif (self.game.home_team_won is True and self.away_score_in_period > self.home_score_in_period) or \
                     (self.game.home_team_won is False and self.away_score_in_period < self.home_score_in_period):
                    return 'held_on'
            else:
                return ''

    def __filter_sentence_content(self, l: list, content_list: str):
        from random import randint
        choice_arr = []
        self.general_scenario = content_list

        if self.is_final_period is True:
            fil = self.final_period_filter(l, content_list)
            if fil == '':
                return ''
            else:
                choice_arr = [item['content'] for item in l if
                              item['type'] == fil and item['primary_time'] == 'end']


        if len(choice_arr) == 0:

            #preferred - both match, then sub-op A -only time matches, then sub-op B- 'any' and 'general' for that list
            choice_arr = [item['content'] for item in l if
                          item['type'] == self.base_sentence_type and item['primary_time'] == self.primary_time]

        if len(choice_arr) == 0:
            # Sub-Op A: Only time matches
            choice_arr = [item['content'] for item in l if
                          item['type'] == 'general' and item['primary_time'] == self.primary_time]

        if len(choice_arr) == 0 and self.is_final_period is False:
            # Sub-Op B: Any and General
            choice_arr = [item['content'] for item in l if
                          item['type'] == 'general' and item['primary_time'] == 'any']

        if len(choice_arr) == 0:
            logging.info("ERROR IN FILTER SENTENCE CONTENT ALGORITHM")
            return ''

        actual_content = deepcopy(choice_arr[randint(0, len(choice_arr)-1)])

        article_language = 'en'
        if hasattr(self.customer_config, 'article_language') and self.customer_config.article_language and type(actual_content) is dict and self.customer_config.article_language in actual_content:
            article_language = self.customer_config.article_language
        actual_content = actual_content[article_language]
        return actual_content

    def get_base_sentence(self):
        s = ''
        
        if self.is_final_period is True:
            home_score_for_check = self.home_score_in_period
            away_score_for_check = self.away_score_in_period
            
            if self.home_score_overall != self.game.home_team_score or self.away_score_overall != self.game.away_team_score:
                logging.info('bad score - no L3 article')
                return ''
            
        else:
            home_score_for_check = self.home_score_overall
            away_score_for_check = self.away_score_overall

        if self.home_score_overall is None:
            logging.info("home team score is none")
            return ''
        elif self.game.winning_score_key in self.current_box and self.game.losing_score_key in self.current_box:
            if self.check_for_neither_scored() is True:
                self.add_period_to_neither_scored()

                self.base_sentence_type = self.get_base_sentence_type(True)
                s = self.__filter_sentence_content(l=self.neither_scored, content_list='neither_scored')

                if self.game.sport_name == 'basketball':
                    s = ''

            elif (home_score_for_check > away_score_for_check and self.game.home_team_won is True) or \
                    (away_score_for_check > home_score_for_check and self.game.home_team_won is False):
                self.base_sentence_type = self.get_base_sentence_type(True)
                s = self.__filter_sentence_content(l=self.winning_winning,content_list='winning_winning')
            elif home_score_for_check == away_score_for_check:
                self.base_sentence_type = self.get_base_sentence_type(True)
                s = self.__filter_sentence_content(l=self.tie,content_list='tie')
            elif (home_score_for_check < away_score_for_check and self.game.home_team_won is True) or \
                    (away_score_for_check < home_score_for_check and self.game.home_team_won is False):
                self.base_sentence_type = self.get_base_sentence_type(True)
                if self.is_final_period is True:
                    s = self.__filter_sentence_content(l=self.winning_winning, content_list='winning_winning')
                else:
                    s = self.__filter_sentence_content(l=self.winning_losing, content_list='winning_losing')
            else:
                s = 'CONTENT GAP.  TIME: %s - BASE ENTENCE TYPE: %s, CONTENT_LIST: - in BASE SENTENCE'%(self.primary_time,self.base_sentence_type)
                logging.info(s)
                s = ''
        else: 
            s = "homeScoreKey' or 'awayScoreKey' not in current box"
            logging.info(s)
            s = ''
        return s

    def __get_small_or_large(self):
        if abs(self.home_score_overall-self.away_score_overall) < self.sport_details.big_win_min-5:
            return ['[[L3_LEAD_SMALL_VERB]]','[[L3_LEAD_SMALL_NOUN]]','[[L3_LEAD_SMALL_ADJ]]']
        else:
            return ['[[L3_LEAD_LARGE_VERB]]','[[L3_LEAD_LARGE_NOUN]]','[[L3_LEAD_LARGE_ADJ]]']
    
    def __get_remove_quarter(self, text):
        if self.period_num >= self.sport_details.normal_num_periods:
            return 'period'
        else:
            if len(self.period_num_list) > 1:
                return self.key_period_name + 's'
            else:
                return self.key_period_name

    def get_l3_output_sentence(self):
        from random import randint
        bs = self.get_base_sentence()
        self.base_sentence = bs
        leads = self.__get_small_or_large()
        
        if bs == '':
            return ''
        
        replace_dict = {
            '[[L3_SCORE]]' : self.score,
            '[[L3_SCORE_IN_PERIOD]]' : self.score_in_period,
            '[[FILLER_BEGINNING_PERIOD_NUM]]' : self.get_filler_period_num(filler_beginning=True),
            '[[FILLER_END_PERIOD_NUM]]' : self.get_filler_period_num(filler_beginning=False),
            '[[L3_OFFENSE_NAME]]' : self.sport_details.offense_name[randint(0, len(self.sport_details.offense_name)-1)],
            '[[L3_DEFENSE_NAME]]' : self.sport_details.defense_name[randint(0, len(self.sport_details.defense_name)-1)],
            '[[L3_LOCKER_ROOM_NAME]]' : self.sport_details.locker_room_name[randint(0, len(self.sport_details.locker_room_name)-1)],
            '[[L3_LEAD_VERB]]' : leads[0],
            '[[L3_HALFTIME_NAME]]' : self.sport_details.halftime_name[randint(0, len(self.sport_details.halftime_name)-1)],
            '[[L3_LEAD_TYPE_NOUN]]' : leads[1],
            '[[L3_LEAD_TYPE_ADJ]]': leads[2],
            
            '[[L3_LEAD_SMALL_VERB]]' : utils.get_item_from_list(l=article_speech_parts.l3_lead_small_verb),
            '[[L3_LEAD_SMALL_NOUN]]' : utils.get_item_from_list(l=article_speech_parts.l3_lead_small_noun),
            '[[L3_LEAD_SMALL_ADJ]]': utils.get_item_from_list(l=article_speech_parts.l3_lead_small_adj),
            '[[L3_LEAD_LARGE_VERB]]': utils.get_item_from_list(l=article_speech_parts.l3_lead_large_verb),
            '[[L3_LEAD_LARGE_NOUN]]':utils.get_item_from_list(l=article_speech_parts.l3_lead_large_noun),
            '[[L3_LEAD_LARGE_ADJ]]':utils.get_item_from_list(l=article_speech_parts.l3_lead_large_adj),
            'fifth quarter': 'first overtime',
            'Fifth quarter': 'First overtime',
            '[[L3_PERIOD]]' : self.__get_remove_quarter(bs),
            '[[L3_ADJ_ARTICLE]]': '' if len(self.period_num_list) > 1 else 'a'
        }

        if self.score is None or self.score == 9999:
            return 'bad score - no L3 article'
        else: 
            for item in replace_dict.keys():
                bs = utils.replace_item_in_string(current=item,in_str=bs,new=replace_dict[item])

        if utils.get_random_int(20) % 2:
            bs = utils.replace_item_in_string(current='[[LOSING_TEAM]]',in_str=bs,new='the [[LOSING_TEAM_MASCOT]]')
            bs = utils.replace_item_in_string(current='[[WINNING_TEAM]]',in_str=bs,new= 'the [[WINNING_TEAM_MASCOT]]')

        bs = utils.replace_items_for_mascot(text=bs)   
        bs = utils.correct_articles_in_text(text=bs)
        bs = utils.capitalize_first_word_in_sentence(s=bs)
        bs = utils.add_period_to_end(bs)
        bs = utils.capitalize_acronyms(text=bs)
        return bs

    def __get_final_output(self):
        return {
            'COMPLETE_SENTENCE': self.sentence,
            'BASE_SENTENCE' : self.base_sentence,
            'PRIMARY_TIME': self.primary_time,
            'BASE_SENTENCE_TYPE' : self.base_sentence_type,
            'GENERAL_SCENARIO' : self.general_scenario,
            'HOME_SCORE_FOR_PERIOD' : self.home_score_overall,
            'AWAY_SCORE_FOR_PERIOD' : self.away_score_overall,
            'HOME_SCORE_IN_PERIOD' : self.home_score_in_period,
            'AWAY_SCORE_IN_PERIOD' : self.away_score_in_period,
            'PERIOD_NUM' : self.period_num_list,
            'HOME_TEAM_WON' : self.game.home_team_won,
        }

    def add_period_to_neither_scored(self):

        neither_scored_list = list(filter(lambda x: x['GENERAL_SCENARIO'] == 'neither_scored', self.l3_data_list))

        if neither_scored_list:
            self.period_num_list = neither_scored_list[0]['PERIOD_NUM'] + [self.period_num]

            for x in self.l3_data_list:
                if x['GENERAL_SCENARIO'] == 'neither_scored':
                    x['COMPLETE_SENTENCE'] = ''

class L2Data:

    def __init__(self, squad_data, lead, game, home_team_data, away_team_data, all_game_data, apa_format_month):
        
        self.lead=lead
        
        self.game = game
        self.all_game_data = all_game_data
        self.article_code = self.all_game_data.l2_data.article_code
        
        self.home_team_data = home_team_data
        self.away_team_data = away_team_data
        self.squad_data = squad_data
        self.apa_format_month = apa_format_month

        self.site_name = self.__get_site_name()
        
        self.winning_team_score = self.__get_score()[0]
        self.losing_team_score = self.__get_score()[1]
        self.base_score_string = self.__get_score_string()
        
        self.key_period_name = self.get_key_period_name()

        self.game_played_date = self.__get_game_day()
        self.state = self.__get_state()

        if self.squad_data.squad_id == 8210 or self.squad_data.squad_id == 8211:
            self.winning_team_name = self.determine_winning_team()[0].team_name_ap
            self.losing_team_name = self.determine_winning_team()[1].team_name_ap
        else:
            self.winning_team_name = self.determine_winning_team()[0].team_name_min
            self.losing_team_name = self.determine_winning_team()[1].team_name_min

        self.winning_team_mascot_name = self.determine_winning_team()[0].mascot
        self.losing_team_mascot_name = self.determine_winning_team()[1].mascot

    def __get_site_name(self):
        return self.home_team_data.team_name_colloquial
    
    def __get_state(self):
        from utils import utils
        if self.home_team_data.state in utils.state_dict: return utils.state_dict[self.home_team_data.state]
        elif self.home_team_data.state is not None: return self.home_team_data.state
        elif self.away_team_data.state is not None: return self.away_team_data.state
        else: return ''
    
    def determine_winning_team(self):
        if self.game.home_team_score > self.game.away_team_score:
            return self.home_team_data, self.away_team_data
        else:
            return self.away_team_data, self.home_team_data
        
    def __get_score(self):
        if self.game.home_team_score > self.game.away_team_score:
            return self.game.home_team_score, self.game.away_team_score
        else:
            return self.game.away_team_score, self.game.home_team_score
        
    def __get_score_string(self):
        return '%i-%i' %(self.winning_team_score,self.losing_team_score)
    
    def get_key_period_name(self):
        if '-' in self.game.game_segment_type:
            return self.game.game_segment_type[:-2]
        else:
            return self.game.game_segment_type
        
    def __get_game_day(self):
        if self.apa_format_month:
            return '%s %s' % (utils.get_apa_month_name(self.game.start_date_time.month), self.game.start_date_time.strftime("%-d")) 
        else:
            return '%s %s' % (self.game.start_date_time.strftime("%B"), self.game.start_date_time.strftime("%-d"))

        
        
        
        

   
                     
        


