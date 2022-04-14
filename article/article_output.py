"""
Articleoutput - Publishes article output based on the level of publishing supplied by the caller.
                It also applies certain levels of beautification not limited to capitalization of
                sentences, adding line between sentences etc. Currently supports development text,
                pre-production text, html and plain text.
"""
from hashlib import new
from article import article_write as rsw
from article import article_data
from utils import utils
import logging
from collections import namedtuple
from profanity_check import predict
from nudenet import NudeClassifier
import traceback
import boto3
import os
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class ArticleOutput:
    
    def __init__(self, l2_data: article_data.L2Data,
                 l3_data:str, trailer_boiler_plate, hashtag_keywords,
                 deep_link_article,
                 is_recap:bool = False):
        
        self.l2_data = l2_data
        self.l3_data = l3_data
        self.is_recap = is_recap ##if it's a recap, change to True and we will change the HTML output.
        self.deep_link_article = self.__init_deep_link(deep_link_article)
        self.headline = ''

        self.trailer_boiler_plate = trailer_boiler_plate
        self.hastag_keywords = self.__get_hashtag_keywords(hashtag_keywords)
        self.placeholder_text = self.__get_placeholder_article()
        self.pre_production_text = self.__get_pre_prod_text()
        self.pre_production_text_html = self.__get_pre_prod_text_html()
        self.plain_text = self.__get_plain_text()
        self.development_text = self.__get_development_text()
        self.html_text = self.__get_html_text()
        self.html_text_with_headline = self._get_html_text_with_headline()

    def __init_deep_link(self, deep_link_article):

        deep_link_template = {'yearly_article': {'txt': '', 'html': ''},
                              'weekly_articles': {'txt': '', 'html': ''}}

        if not deep_link_article:
            deep_link_article = namedtuple('DeepLink', deep_link_template.keys())(*deep_link_template.values())
        return deep_link_article

    def __get_placeholder_article(self):
        
        base_article = self.l2_data.lead
        base_article = utils.correct_articles_in_text(text=base_article)

        l3_article = self.l3_data
        headline = self.l2_data.all_game_data.l2_data.headline
        headline = utils.capitalize_acronyms(text=headline)
        headline = utils.correct_articles_in_text(text=headline)
        
        written_article = base_article + '\n' + l3_article

        written_article = headline + '\n' + written_article

        return written_article

    def __get_plain_text(self):
        headline = rsw.replace_article_data(written_article=self.l2_data.all_game_data.l2_data.headline,ad=self.l2_data)
        headline = utils.capitalize_acronyms(text=headline)
        headline = utils.correct_articles_in_text(text=headline)
        self.headline = headline
        
        return headline + '\n' + self.pre_production_text + self.trailer_boiler_plate['text']
        
    def __get_pre_prod_text(self):
        
        base_article = rsw.replace_article_data(written_article=self.l2_data.lead,ad=self.l2_data)
        base_article = utils.capitalize_acronyms(text=base_article)
        base_article = utils.correct_articles_in_text(text=base_article)

        l3_article = rsw.replace_article_data(written_article=self.l3_data, ad=self.l2_data)

        if self.deep_link_article.yearly_article['txt'] and self.deep_link_article.weekly_articles['txt']:
            written_article = base_article + '\n\n' + self.deep_link_article.yearly_article['txt'] + '\n' + l3_article + '\n' + \
                              self.deep_link_article.weekly_articles['txt']

        else:
            if utils.get_random_int(10) % 2:
                written_article = base_article + '\n\n' + self.deep_link_article.weekly_articles['txt'] + \
                                  self.deep_link_article.yearly_article['txt'] + '\n' + l3_article + '\n'
            else:
                written_article = base_article + '\n' + l3_article + '\n\n' + self.deep_link_article.weekly_articles['txt'] + \
                                  self.deep_link_article.yearly_article['txt'] + '\n'

        written_article = utils.remove_double_word(text=written_article)

        return written_article

    def __get_pre_prod_text_html(self):

        base_article = rsw.replace_article_data(written_article=self.l2_data.lead, ad=self.l2_data)
        base_article = utils.capitalize_acronyms(text=base_article)
        base_article = utils.correct_articles_in_text(text=base_article)

        l3_article = rsw.replace_article_data(written_article=self.l3_data, ad=self.l2_data)

        if self.deep_link_article.yearly_article['html'] and self.deep_link_article.weekly_articles['html']:
            written_article = base_article + self.deep_link_article.yearly_article['html'] + l3_article + '\n' + \
                              self.deep_link_article.weekly_articles['html']

        else:
            if utils.get_random_int(10) % 2:
                written_article = base_article + self.deep_link_article.weekly_articles['html'] + \
                                  self.deep_link_article.yearly_article['html'] + '\n' + l3_article
            else:
                written_article = base_article + '\n' + l3_article + self.deep_link_article.weekly_articles['html'] + \
                                  self.deep_link_article.yearly_article['html']

        written_article = utils.remove_double_word(text=written_article)

        return written_article

    def __get_development_text(self):
        
        '''
        Development text is text with much of the data going into the article available in raw form as well.
        We do this to make sure that the articles we are writing are accurate 
        '''
        sport = self.l2_data.all_game_data.individual_game.sport_name
        box = self.l2_data.all_game_data.individual_game.box_scores
        game_id = self.l2_data.all_game_data.individual_game.game_id
        game_url = self.l2_data.all_game_data.individual_game.url

        
        box_string = ''
        article_code = self.l2_data.article_code
    
        for item in box:
            box_string = box_string + utils.convert_box_to_str(item) + '\n'

        article_and_data = self.plain_text + '\n\n' + 'SPORT: %s'%sport + '\n\n' + 'ARTICLE CODE: %i'%article_code \
                           + '\n\n' + 'GAME URL:\n%s' % game_url + '\n\n' + 'GAMEID:\n%i'%game_id + '\n\n' \
                           + 'BOX SCORE:\n%s' % box_string + '\n' + 'HOME TEAM: %s          AWAY TEAM: %s'\
                           %(self.l2_data.home_team_data.team_name_short, self.l2_data.away_team_data.team_name_short) \
                           + '\n' + 'WINNING TEAM: %s %s          LOSING TEAM: %s %s'%\
                           (self.l2_data.winning_team_name, self.l2_data.winning_team_mascot_name,
                            self.l2_data.losing_team_name, self.l2_data.losing_team_mascot_name)
        return article_and_data

    def __get_html_text(self):
        publish_article = self._get_html_main_content() + self.trailer_boiler_plate['html'] + self.hastag_keywords
        publish_article = utils.replace_item_in_string(current='</p><p></p>',in_str=publish_article, new='</p>')
        return publish_article

    def _get_html_text_with_headline(self):
        article_html_with_headline = '<b>' + self.headline + '</b>' + self._get_html_main_content()
        article_html_with_headline = utils.replace_item_in_string(current='</p><p></p>',
                                                                  in_str=article_html_with_headline, new='</p>')
        return article_html_with_headline

    def _get_html_main_content(self):
        publish_article = '<p>' + self.pre_production_text_html + '</p>'
        publish_article = utils.replace_item_in_string(current='\n',in_str=publish_article,new='</p><p>')
        publish_article = utils.replace_item_in_string(current='</p></p>', in_str=publish_article, new='</p>')
        return publish_article

    def __get_hashtag_keywords(self, hashtag_keywords):
        hashtag_str = ""
        if hashtag_keywords:
            try:
                if 'sport_name' in hashtag_keywords:
                    if self.l2_data.all_game_data.sport_details.both_genders is not True:
                        hashtag_str += "#" + self.l2_data.all_game_data.individual_game.sport_name
                    else:
                        hashtag_str += "#" + self.l2_data.all_game_data.squad_data.gender + \
                                       self.l2_data.all_game_data.individual_game.sport_name
                if 'home_team' in hashtag_keywords:
                    hashtag_str +=  ", #" + self.l2_data.home_team_data.team_name
                if 'away_team' in hashtag_keywords:
                    hashtag_str += ", #" + self.l2_data.away_team_data.team_name
            except Exception as e:
                logging.info("expection in hanlding the attirbute")
        hashtag_str = '<p>' + hashtag_str + '</p>'
        return hashtag_str


class SeniorSpotLightOutput:

    def __init__(self, item, customer_config, general_config):
        self.item = item
        self.customer_config = customer_config
        self.general_config = general_config
        self.status_text = self._format_senior_spotlight_output()
        self.html_text = self.status_text['content']
        self.html_img = self.status_text['img_link']

    def _format_senior_spotlight_output(self):
        output_string = ''
        output_dict = {'raw_item': self.item}

        img_link = "https://{0}.s3.amazonaws.com/{1}".format(
            self.general_config['senior_spot_light_s3'],
            self.item['senior_photo'])
        output_dict['img_link'] = img_link

        try:
            output_template = [
                            '<p>Full Name: {}</p>',
                            '<p>High School: {}</p>',
                            '<p>Accomplishments: {}</p>',
                            '<p>Future Plans: {}</p>',
                            '<p>List Of Extracurriculars: {}</p>',
                            '<p>Favorite Quote: {}</p>',
                            '<p>Personal Message To Your Senior: {}</p>',
                            '<p>Parent 1 Name: {}</p>',
                            '<p>Parent 2 Name: {}</p>'
                             ]

            key_list = ['full_name',
                        'high_school',
                        'accomplishments',
                        'future_plans',
                        'list_of_extracurriculars',
                        'favorite_quote',
                        'personal_message_to_your_senior',
                        'parent_1_name',
                        'parent_2_name']

            for each_op_template, key in zip(output_template, key_list):
                if self.item[key] and self.item[key] != '':
                    output_string += each_op_template.format(self.item[key])
            self.article_id = str(self.item['high_school']).replace(' ', '_') + '_' + \
                str(self.item['full_name']).replace(' ', '_') + '_' + str(uuid.uuid4())

            high_school = str(self.item['high_school']).title()
            current_year_graudate = ' ' + str(datetime.now().year) + ' Graduate: '
            self.headline = high_school + current_year_graudate + self.item['full_name']

            if output_string and output_string != '' and self.check_for_profanity([output_string]):
                output_string = self.customer_config.senior_spotlight_sponsor + output_string
                if 'senior_photo' in self.item and self.item['senior_photo']:
                    s3 = boto3.client('s3')
                    s3.download_file(self.general_config['senior_spot_light_s3'], self.item['senior_photo'],
                                     os.path.join('logs', self.item['senior_photo']))

                    if self.check_for_nude_images(os.path.join('logs', self.item['senior_photo'])):
                        output_dict.update({'content': output_string, 'status': 'success'})
                        output_dict.update({'content': output_string, 'status': 'success'})
                    else:
                        logging.error("Image -%s might have nudity in it", repr(img_link))
                        output_dict.update({'content': output_string, 'status': 'failure', 'reason': 'nudity'})
                    os.remove(os.path.join('logs', self.item['senior_photo']))

            else:
                logging.error("Error Processing output string , may have profane content")
                output_dict.update({'content': output_string, 'status': 'failure', 'reason': 'profanity'})

        except:
            logging.error("Encountered while formatting senior spotlights " + traceback.format_exc())
            output_dict.update({'content': output_string, 'status': 'error'})

        finally:
            return output_dict


    @staticmethod
    def check_for_profanity(input_string):
        profanity = predict(input_string)
        logging.info(repr(profanity))
        if profanity and profanity[0]:
            logging.error("Profane content detected in %s", repr(input_string))
            return False
        else:
            return True

    @staticmethod
    def check_for_nude_images(image_link):
        classifier = NudeClassifier()
        img_output = classifier.classify(image_link)

        if img_output and image_link in img_output and 'safe' in img_output[image_link] \
                and 'unsafe' in img_output[image_link] and img_output[image_link]['safe'] > img_output[image_link]['unsafe']:
            logging.info('Image with link %s is found to be safe')
            return True
        else:
            logging.error('Image with link %s is found to be unsafe')
            return False




