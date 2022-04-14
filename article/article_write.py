"""

Does two major functions. calls the necessary function to arrive at the article output and replaces
the placeholder in the article text with the appropriate fields.

"""

from utils import utils
from article import article_data, article_output
from games import agd as agd
from games import game_details
import random
import logging
import re
from article import deep_link
import traceback
import threading
import json
from db import dynamo
from games import sport_details as sd

logger = logging.getLogger(__name__)


def replace_article_data(written_article:str, ad):

    logging.info("Starting to replace data in article \n")

    written_article = replace_squad_level(written_article=written_article, ad=ad)
    written_article = replace_mascot_name(written_article=written_article, ad=ad)

    replacement_dict1 = {
                        '[[SCORE]]': ad.base_score_string,
                        '[[NUM]]': utils.number_dict[ad.all_game_data.sport_details.num_periods_for_early],
                        '[[LEAD_CHANGE_NUM]]': utils.number_dict[ad.all_game_data.sport_details.num_periods_for_early+1],
                        '[[IN_LINE_ARTICLE]]': 'a',
                        '[[SITE]]': utils.convert_to_title(ad.all_game_data.home_team_data.team_name_short),
                        '[[KEY_PERIOD]]': ad.key_period_name,
                        '[[SQUAD_DISPLAY]]': ad.all_game_data.squad_data.gender_level_display.lower() if ad.all_game_data.sport_details.both_genders else '',
                        '[[SPORT]]': ad.all_game_data.individual_game.sport_name.lower(),
                        '[[FILLER]].': '',
                        '[[STATE]]': ad.state,
                        '[[DATE]]': ad.game_played_date,

                        '[[OVERTIME_NAME]]':  random.choice(ad.all_game_data.sport_details.overtime_names) if ad.all_game_data.sport_details.overtime_names else "",
                        '[[DEFENSE_NAME]]': random.choice(ad.all_game_data.sport_details.defense_name) if ad.all_game_data.sport_details.defense_name else "",
                        '[[DEFENSE_ADJ]]': random.choice(ad.all_game_data.sport_details.defense_adj) if ad.all_game_data.sport_details.defense_adj else "",
                        '[[DEFENSE_SUFFIX]]': random.choice(ad.all_game_data.sport_details.defense_suffix) if ad.all_game_data.sport_details.defense_suffix else "",

                        '[[SCORE_NAME]]': ad.all_game_data.sport_details.score_name,
                        '[[OVERTIME_NAME_BEGINNING]]': 'extra %s' % ad.all_game_data.individual_game.sport_name,
                        '[[AMT_SCORED_IN_KEY_PERIOD]]': str(ad.all_game_data.sport_details.score_early_team_min),
                        '[[PERIOD]]': str(ad.all_game_data.individual_game.game_segment_type),
                        '[[TOTAL_NUM_PERIODS]]': str(len(ad.all_game_data.individual_game.box_scores) - 1),
                        '[[DAY_OF_WEEK]]': ad.all_game_data.individual_game.game_day_str,
                        '[[L3_HALFTIME_NAME]]': 'the break',
                        '[[LOCATION]]': ad.site_name,
                        '[[WINNING_TEAM]]': ad.winning_team_name,
                        '[[LOSING_TEAM]]': ad.losing_team_name

    }
    replacement_dict2 = {
                        'Varsity': '',
                        'varsity': '',
                        "'S": "'s",
                        "S'": "s'",
                        'ST ': 'St. ',
                        'MT ': 'Mt. ',
                        'Mt ': 'Mt. ',
                        'St ': 'St. ',
                        "the halftime": "halftime",
                        "Nothing were": "Nothing was",
                        "Boys": "boys",
                        "Womens": "women's",
                        "Mens": "men's",
                        "Girls": "girls",
                        "High School": "high school",
                        " ncaa": " NCAA",
                        " nba": " NBA",
                        " mlb": " MLB",
                        " nfl": " NFL",
                        " mls": " MLS",
                        " wnba": " WNBA",
                        " nhl": " NHL",
                        ". .": "",
                        "..": "."
    }

    written_article = _replace_regex_items(written_article=written_article, replacement_dict=replacement_dict1)
    written_article = _replace_regex_items(written_article=written_article, replacement_dict=replacement_dict2)

    written_article = written_article.replace("s's", "s'")
    # Replace any double spaces
    written_article = written_article.replace("  ", " ")
    written_article = written_article.replace("..", ".")
    written_article = written_article.replace(". .", ".")
    # if ad.base_score_string == '0 - 0': return None
    if written_article is None:
        logging.info("written article is none \n")
        return
    else:
        logging.info("Completed replacing the data in the  article\n")
        return written_article


def _replace_regex_items(written_article, replacement_dict):
    rep = dict((re.escape(k), v) for k, v in replacement_dict.items())
    pattern = re.compile("|".join(rep.keys()))
    written_article = pattern.sub(lambda m: rep[re.escape(m.group(0))], written_article)
    return written_article


def replace_squad_level(written_article, ad):
    if ad.all_game_data.sport_details.both_genders is True:
        written_article = written_article.replace('[[SQUAD_LEVEL]]', ad.all_game_data.squad_data.short_display)
    else:
        written_article = written_article.replace('[[SQUAD_LEVEL]]', ad.all_game_data.squad_data.level.lower())
    return written_article


def replace_mascot_name(written_article, ad):
    if ad.winning_team_mascot_name != ad.losing_team_mascot_name:
        # if both teams have different mascots, we can use them
        logging.info("Mascot Names of winning team and losing team are different\n")
        written_article = written_article.replace('[[WINNING_TEAM_MASCOT]]', ad.winning_team_mascot_name)
        written_article = written_article.replace('[[LOSING_TEAM_MASCOT]]', ad.losing_team_mascot_name)

    else:
        logging.info("Mascot Names of winning team and losing team are same\n")
        # if both teams are the cardinals, use team names only

        written_article = written_article.replace('the [[WINNING_TEAM_MASCOT]]', ad.winning_team_name)
        written_article = written_article.replace('the [[LOSING_TEAM_MASCOT]]', ad.losing_team_name)
        written_article = written_article.replace('The [[WINNING_TEAM_MASCOT]]', ad.winning_team_name)
        written_article = written_article.replace('The [[LOSING_TEAM_MASCOT]]', ad.losing_team_name)
    return written_article


def write_one_article(g: dict, written_article_indices: dict, customer_config):

    logging.info("Preparing to write the article\n")

    output_dict = {}

    deep_link_thread = threading.Thread(target=execute_deep_linking,
                                        args=(customer_config, game_details.Game(game_dict=g), output_dict))

    deep_link_thread.start()

    all_data = agd.AllGameData(game_dict=g, written_article_indices=written_article_indices,
                               customer_config=customer_config)
    l3_data = all_data.l3_data

    if all_data.l2_data is None:
        logging.info("L2 DATA IS NONE FOR SPORT: %s %d", g['sportName'], g['gameId'])
        return None

    if all_data.l2_data.article_code is None:
        logging.info("No rules for game - %s %d", g['sportName'], g['gameId'])
        return None

    lead = all_data.l2_data.lead

    logging.info("Initialize  the L2 data\n")

    apa_format_month = utils.get_apa_format_month(customer_config)

    logging.info("Apa format for month is set to be %s", repr(apa_format_month))

    ad = article_data.L2Data(squad_data=all_data.squad_data, away_team_data=all_data.away_team_data,
                             lead=lead, game=all_data.individual_game,
                             home_team_data=all_data.home_team_data, all_game_data=all_data, apa_format_month=apa_format_month)
    l3_text = ""
    if all_data.sport_details.sports_detail_allowed:
        l3_text = get_l3_article_text(all_data=all_data, customer_config=customer_config)

    if hasattr(customer_config, 'headline_score') and customer_config.headline_score:
        ad.all_game_data.l2_data.headline = ad.all_game_data.l2_data.headline + ' ' + ad.base_score_string

    deep_link_thread.join()

    deep_link_article = output_dict['deep_link']

    article = article_output.ArticleOutput(l2_data=ad, l3_data=l3_text,
                                           trailer_boiler_plate=customer_config.trailer_boiler_plate,
                                           hashtag_keywords=customer_config.hashtag_keywords if
                                           hasattr(customer_config, 'hashtag_keywords') else [],
                                           deep_link_article=deep_link_article)
    return article


def execute_deep_linking(customer_config, game, output_dict):
    deep_link_flag = True
    if hasattr(customer_config, 'deep_link_flag'):
        deep_link_flag = customer_config.deep_link_flag

    deep_link_article = None

    sport_details = get_sport_details(game=game, customer_config=customer_config)
    try:
        if deep_link_flag and sport_details:
            logging.info("Writing the deep link article\n")

            deep_link_article = deep_link.DeepLink(game=game,
                                                   sports_config=sport_details,
                                                   customer_config=customer_config)
    except Exception as e:
        logging.info("error in writing the deep link article\n" + repr(e))
        logging.info(traceback.format_exc())
        pass

    finally:
        output_dict['deep_link'] = deep_link_article


def get_l3_article_text(all_data: agd.AllGameData, customer_config):

    l3_data = all_data.l3_data

    all_sentences = []

    neither_scored = []

    last_l3_item = l3_data[len(l3_data) - 1]

    if last_l3_item['BASE_SENTENCE_TYPE'] == 'lead_change' and \
       (last_l3_item['GENERAL_SCENARIO'] == 'neither_scored' or last_l3_item['GENERAL_SCENARIO'] == 'tie') and \
       utils.get_random_int(20) % 2 == 0:
        logging.info("Reversal of L3 data is False\n")

    elif hasattr(customer_config, 'L3_data_reverse') and customer_config.L3_data_reverse is False:
        logging.info("Reversal of L3 data is False\n")
    # else:
    #     logging.info("Reversal of L3 data is True\n")
    #     l3_data.reverse()

    for item in l3_data:
        if item['GENERAL_SCENARIO'] == 'neither_scored':
            if all_data.individual_game.sport_name == 'basketball':
                all_sentences = ['']
                logging.info("No L3 data since basketball cannot have neither scored period")
                break
            neither_scored.append(item)

        if 'L3' in item['COMPLETE_SENTENCE']:
            all_sentences = ['']
            break
        else:
            all_sentences.append(item["COMPLETE_SENTENCE"] + '\n')

    if len(neither_scored) == len(l3_data):
        all_sentences = ['']

    l3_text = "\n".join(all_sentences)
    return l3_text


def get_sport_details(game, customer_config):
    sport_name = game.sport_name

    sports_config = list(filter(lambda x : x['sport_name'] == sport_name, customer_config.sports_config))

    if sports_config:
        logging.info(" Sport %s is defined in the configuration", sport_name)
        if len(sports_config) > 1:
            sports_config = list(filter(lambda x : x['normal_num_periods'] == len(game.box_scores)-1,
                                        sports_config))[0]
        else:
            sports_config = sports_config[0]

        sport_details = sd.Sports(sports_config=sports_config)

        return sport_details
    else:
        logging.info(" Sport %s is not defined in the configuration", sport_name)
        return None
