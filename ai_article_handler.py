"""
This is the main module , a kind of orchestrator which handles the request from the scheduler
and executes the job with necessary parameters provided by the scheduler.

Main functions is not limited to
Retrieving customer config,
calculating the necessary date range,
fetching games from score stream,
upload games to the database,
apply the necessary filters on the games,
write articles ,
publish articles if needed to Blox, Wordpress etc.
"""
import logging
import json
import os
import io
import time
import threading
from db import dynamo
import traceback
from utils import dates, utils
from article import article_write
from customer.customer_config import CustomerConfig
from customer.games_filter import GameFilter
from datetime import datetime, timedelta
from string import Template
from scorestream import ss_integration
from publisher import stats, publish_handler
from publisher.dynamo_log import log_in_ddb, log_in_alt_table
import sys
from pandas import DataFrame
from article.article_output import SeniorSpotLightOutput
from sqs import sqs
from s3 import s3
import config

if not os.path.exists("logs"):
    os.makedirs("logs")


# Remove all handlers associated with the root logger object.


logging.basicConfig(level=getattr(logging, "INFO"),
                    format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
                    handlers=[
                        logging.StreamHandler(sys.stdout)
                    ])
root_logger = logging.getLogger()
root_handler = root_logger.handlers[0]
orig_factory = logging.getLogRecordFactory()

def process_article_request(customer_name, general_config, fixed_date_time=None,
                            game_range_days=0,
                            run_time_id="default",
                            delete_files=True,
                            current_date_time=datetime.now(),
                            article_numbers_only=False):

    try:
        customer_config = CustomerConfig(customer_name, general_config=general_config)
    except ValueError:
        customer_config = None

    if customer_config:

        if fixed_date_time is None:
            fixed_date_time = datetime.now()

        offset_days = utils.get_scheduler_offset(general_config=general_config)
        if hasattr(customer_config, 'offset_days'):
            offset_days = customer_config.offset_days
        today_datetime = fixed_date_time - timedelta(days=offset_days)

        modify_output_file(today_datetime=today_datetime, customer_config=customer_config)

        date_range = get_date_range(customer_config=customer_config, today_datetime=today_datetime,
                                    game_range_days=game_range_days)
        try:
            collection = ss_integration.get_games_for_location(location_arr=customer_config.location, date_range=date_range)

            # Populate the list of teams and sqaud ids after getting the games

            games_list, teams_list, squad_list = get_details_from_collections(collection=collection)

            customer_config.coverage_team_list = customer_config.get_list_of_teams_by_sport(teams_list)
            customer_config.coverage_squad_list = customer_config.get_list_of_squads_by_sport()

            filtered_games, article_run_detailed_info = get_filtered_games(customer_config=customer_config,
                                                                           date_range=date_range,
                                                                           games_list=games_list, teams_list=teams_list)

            if hasattr(customer_config, 'article_numbers_only') and customer_config.article_numbers_only:
                article_numbers_only = customer_config.article_numbers_only

            if not article_numbers_only:

                upload_to_dynamo(games_list=filtered_games, teams_list=teams_list, squad_list=squad_list,
                                 general_config=general_config)

                del games_list
                del teams_list
                del squad_list

                articles, stats_details, posted_urls, csv_s3_url = process_all_games(filtered_games, customer_config, run_time_id,
                                                                                     current_datetime=current_date_time,
                                                                                     article_run_detailed_info=article_run_detailed_info,
                                                                                     )

                logging.info("The number of articles written are  %d", len(articles))
                try:
                    send_report_email(customer_config=customer_config, articles=articles,
                                      stats_details=stats_details, today_datetime=today_datetime,
                                      posted_urls=posted_urls, delete_files=delete_files)
                except Exception:
                    logging.exception("error in sending email")
            else:
                logging.info("Number of valid games received is %d", len(filtered_games))

                message = "Number of valid games received for {0} are {1}".format(customer_name, len(filtered_games))

                subject = general_config['product_name'] + ' -' + customer_config.name + ' -' + general_config['published_status'] + \
                          '-' + today_datetime.strftime("%Y-%m-%d") + "(" + general_config['system_name'] + ")"

                s3_bucket = general_config['article_s3_bucket']

                csv_s3_url = upload_to_s3_and_write_file(s3_bucket=s3_bucket,
                                                         article_run_detailed_info=article_run_detailed_info,
                                                         run_time_id=run_time_id,
                                                         current_datetime=today_datetime,
                                                         customer_config=customer_config)
                message += "\n\n<p></p>"
                message += "S3 URL with the csv list - {0}".format(csv_s3_url)

                emails = []

                if customer_config.editor_email:
                    emails += [customer_config.editor_email]
                if customer_config.publisher_email:
                    emails += [customer_config.publisher_email]
                if customer_config.additional_contact_emails_for_articles:
                    emails += customer_config.additional_contact_emails_for_articles
                
                emails = list(set(emails))

                utils.send_aws_email(msg_html=message, send_from='content@ledeai.com',
                                     send_to=emails,
                                     subject=subject, files=[], filenames=[])

        except KeyboardInterrupt:
            logging.exception("error in fetching games from scorestream")
    else:
        message = "Customer Config not found for " + customer_name

        utils.send_aws_email(msg_html=message, send_from='content@ledeai.com', send_to=general_config['alert_emails'],
                             subject=message, files=[], filenames=[])


def upload_to_s3_and_write_file(s3_bucket, article_run_detailed_info, customer_config, current_datetime, run_time_id):
    logging.info("writing the game detailed info to S3 and to file")
    csv_file_buf = io.StringIO()
    article_run_detailed_info_csv = DataFrame(data=article_run_detailed_info)
    article_run_detailed_info_csv.to_csv(csv_file_buf)
    csv_file_buf.seek(0)

    csv_value = csv_file_buf.getvalue()

    csv_file_buf = io.BytesIO(bytes(csv_value, encoding='utf-8'))
    csv_file_buf.seek(0)

    current_date = current_datetime.strftime("%Y-%m-%d")
    current_time = current_datetime.strftime("%H-%M")

    csv_file_s3_key = os.path.join(customer_config.name, current_date, current_time, run_time_id + '.csv')
    csv_file_name = customer_config.article_output_file.replace('.txt', '.csv')

    csv_s3_url = s3.upload_to_aws(s3_bucket=s3_bucket, file_data=csv_file_buf, s3_key=csv_file_s3_key,
                                  extra_args={'ACL': 'public-read'})

    with open(csv_file_name, 'w+') as tf:
        tf.write(csv_value)
    return csv_s3_url


def upload_to_dynamo(games_list, teams_list, squad_list, general_config):

    recommended = [(games_list, general_config['games_table']),
                   (teams_list, general_config['teams_table']),
                   (squad_list, general_config['squads_table'])]
    for item in recommended:
        logging.info("Uploading to the %s table", item[1])
        dynamo.dynamo_batch_put_item(entry=item[0], table_name=item[1])
        logging.info("Uploading to the %s table complete", item[1])


def get_details_from_collections(collection):
    games_list = []
    teams_list = []
    squads_list = []

    if 'collections' in collection:
        if 'gameCollection' in collection['collections'] and 'list' in collection['collections']['gameCollection']:
            games_list = collection['collections']['gameCollection']['list']
        if 'teamCollection' in collection['collections'] and 'list' in collection['collections']['teamCollection']:
            teams_list = collection['collections']['teamCollection']['list']
        if 'squadCollection' in collection['collections'] and 'list' in collection['collections']['squadCollection']:
            squads_list = collection['collections']['squadCollection']['list']

    return games_list, teams_list, squads_list


def process_all_games(game_list: list, customer_config, run_time_id="default",
                      current_datetime=datetime.now(), article_run_detailed_info=[]):
    articles = []
    article_num = 1
    written_article_indices = {}
    publisher_handle = publish_handler.HandlePublish(customer_config=customer_config)
    article_in_files = {'new_games': '', 'old_games': ''}
    articles_new = {'new_games': [], 'old_games': []}
    game_id_lists = []

    for game_index, game in enumerate(game_list, start=1):
        try:
            logging.setLogRecordFactory(record_factory_factory(customer_name=customer_config.name, article_type="article",game_id=str(game['gameId'])))
            formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] - [%(customer_name)s] - [%(game_id)s]   %(message)s")
                
            root_handler.setFormatter(formatter)

            logging.info("preparing to write article - %d", game_index)
            
            if game['gameId'] in game_id_lists:
                logging.info("game - %d has already been processed in this run, hence ignoring")
                continue

            if 'gameId' in game:
                game_id_lists.append(game['gameId'])
            
            article = article_write.write_one_article(g=game, written_article_indices=written_article_indices,
                                                      customer_config=customer_config)

            if article is None:
                logging.info("ARTICLE IS NONE FOR GAMEID %d", game['gameId'])
                continue

            else:
                # Open file in write mode first and then subsequent articles would be in append mode
                try:

                    articles.append(article)

                    store_article_content(customer_config=customer_config,
                                          article_in_files=article_in_files,
                                          article=article, articles_new=articles_new)
                    # add_meta_tags(meta_tags=meta_tags, article=article)

                    ddb_id = customer_config.name + '_' + \
                             str(article.l2_data.all_game_data.individual_game.home_team_id) + '_' + \
                             str(article.l2_data.all_game_data.individual_game.home_squad_id) + '_' \
                             + article.l2_data.game.sport_name + '_' + 'file'

                    ddb_alt_id = customer_config.name + '_' + \
                             str(article.l2_data.all_game_data.individual_game.away_team_id) + '_' + \
                             str(article.l2_data.all_game_data.individual_game.home_squad_id) + '_' \
                             + article.l2_data.game.sport_name + '_' + 'file'

                    game_start_time = article.l2_data.all_game_data.individual_game.utc_start_date_time

                    log_in_ddb(asset_id=ddb_id,
                               game_start_time=game_start_time,
                               sport_name=article.l2_data.game.sport_name,
                               squad_id=str(article.l2_data.game.home_squad_id),
                               customer_name=customer_config.name,
                               customer_id=customer_config.id,
                               post_url=customer_config.article_output_file,
                               game_id=game['gameId'],
                               home_team_id=game['homeTeamId'],
                               away_team_id=game['awayTeamId'],
                               game_url=game['url'],
                               system_type='file',
                               invoice_company=customer_config.invoice_company if hasattr(customer_config,
                                                                    'invoice_company') else customer_config.name,
                               general_config=customer_config.general_config)
                    entry = {
                        'id': ddb_alt_id,
                        'alt_id': ddb_id,
                        'game_start_time': game_start_time
                    }

                    log_in_alt_table(entry, customer_name=customer_config.name,
                                     general_config=customer_config.general_config)

                    article_num += 1

                except Exception as e:
                    logging.error(traceback.format_exc() + "Error writing the article")
                    continue

                try:
                    if hasattr(customer_config,'test_system') and customer_config.test_system and article_num > 2:
                        continue
                    else:
                        publisher_handle.publish_articles(article=article)

                except Exception as e:
                    logging.error(traceback.format_exc() + "Error publishing the article")
                    continue

        except Exception as e:
            logging.exception('Encountered an exception during writting article for game %d', game['gameId'])
            continue
    txt_s3_url = ""
    html_s3_url = ""
    csv_s3_url = ""

    if articles:
        if article_in_files['old_games']:
            article_in_files['old_games'] += articles[-1].trailer_boiler_plate['html']
        if article_in_files['new_games']:
            article_in_files['new_games'] += articles[-1].trailer_boiler_plate['html']
        txt_s3_url, html_s3_url, csv_s3_url = publisher_handle.write_to_file(article_in_files=article_in_files,
                                                                             run_time_id=run_time_id,
                                                                             current_datetime=current_datetime,
                                                                             article_run_detailed_info=article_run_detailed_info)

    if publisher_handle.wp_session_info:
        publisher_handle.logoff_from_wordpress()

    return articles, publisher_handle.get_stats(), publisher_handle.get_posted_urls(), csv_s3_url


def store_article_content(customer_config, article, article_in_files, articles_new,
                          write_article=True):
    if hasattr(customer_config, 'article_publishing_level'):
        article_content = getattr(article, customer_config.article_publishing_level)
    else:
        article_content = article.html_text_with_headline

    st = ''

    # line_sep = False
    # boiler_plate = False

    if item_exists_in_posted_table(article=article, customer_config=customer_config):
        logging.info("Article for game %d has been found in posted assets for customer %s", article.l2_data.game.game_id,
                    customer_config.name)
        bucket_to_be_written = 'old_games'

    else:
        logging.info("Article for game %d has not been found in posted assets for customer %s", article.l2_data.game.game_id,
                    customer_config.name)
        bucket_to_be_written = 'new_games'

    if write_article:
        st = st + '<p>%s</p>' % article_content

    article_in_files[bucket_to_be_written] += st
    articles_new[bucket_to_be_written].append(article)

    logging.info("WRITTEN ARTICLE FOR GAME WITH GAMEID %d", article.l2_data.game.game_id)


def get_filtered_games(customer_config, date_range, games_list, teams_list):

    logging.info("Starting to retrieve the games from the database \n")

    game_filter = GameFilter(customer_config=customer_config, date_range=date_range, games_list=games_list,
                             teams_list=teams_list)
    valid_games = game_filter.games_list
    games_detailed_info = game_filter.article_run_detailed_info

    return valid_games, games_detailed_info


def item_exists_in_posted_table(article, customer_config):
    posted_assets_table = customer_config.general_config['posted_assets_table']
    posted_asset_key = customer_config.name + '_' + \
        str(article.l2_data.game.home_team_id) + '_' + \
        str(article.l2_data.game.home_squad_id) + '_' \
        + str(article.l2_data.game.sport_name.lower()) + '_' + 'file'

    game_start_time = article.l2_data.all_game_data.individual_game.utc_start_date_time
    asset_item = dynamo.dynamo_get_item(table_name=posted_assets_table, keys=['id', 'game_start_time'],
                                        vals=[posted_asset_key, game_start_time])
    if asset_item:
        return True
    else:
        return False


def get_date_range(customer_config, today_datetime, game_range_days):

    if game_range_days > 0:
        logging.info("Game range days greater than 0 - %d", game_range_days)

    utc_range = dates.Dates().utc_date_range(local_date_time=today_datetime, game_range_days=game_range_days,
                                             timezone=customer_config.timezone)
    return utc_range


def modify_output_file(today_datetime, customer_config):
    file_name = Template(customer_config.article_output_file)

    (current_year, this_month, today, _, _, _, _, _, _) = today_datetime.timetuple()

    customer_config.article_output_file = file_name.safe_substitute(year=str(current_year), month=str(this_month),
                                                                    day=str(today))


def process_senior_spotlights(general_config):
    items = dynamo.dynamo_db_scan(table_name=general_config['senior_spot_light'])
    if items:
        for item in items:
            try:
                customer_name = str(item['customer']).title().replace('_', ' ') + ' Local'


                logging.setLogRecordFactory(record_factory_factory(customer_name, 'spotlight'))

                formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] - [%(customer_name)s] - [%(game_id)s]   %(message)s")
                
                root_handler.setFormatter(formatter)

                customer_config = CustomerConfig(customer_name=customer_name, general_config=general_config)

                subject = general_config['product_name'] + ' Senior Spotlights -' + customer_config.name + ' -' + "(" + general_config['system_name'] + ")"

                emails = []
                if customer_config.editor_email:
                    emails += [customer_config.editor_email]
                if customer_config.publisher_email:
                    emails += [customer_config.publisher_email]
                if customer_config.additional_contact_emails_for_articles:
                    emails += customer_config.additional_contact_emails_for_articles

                logging.info("Processing senior spotlight article - %s", repr(item))
                senior_spotlight = SeniorSpotLightOutput(item=item,
                                                         general_config=general_config,
                                                         customer_config=customer_config)
                senior_spotlight_article = senior_spotlight.status_text

                if senior_spotlight_article:
                    item['dateAdded'] = item['dateAdded'].isoformat()
                    if 'status' in senior_spotlight_article:
                        if senior_spotlight_article['status'] == 'success':
                            publisher = publish_handler.HandlePublish(customer_config=customer_config, spot_lights=True)
                            publisher.publish_articles(article=senior_spotlight)
                            logging.info("Completed processing senior spotlight article - %s",
                                        repr(senior_spotlight_article))
                            html_msg = customer_config.senior_spotlight_confirmation + '<p></p>' + \
                                       senior_spotlight_article['content']
                            if 'verify_email' in item and item['verify_email'] != '':
                                subject = 'Senior Spotlight Confirmation for ' + item['full_name']
                                utils.send_aws_email(msg_html=html_msg, send_from=customer_config.senior_spotlight_sender_email,
                                                     send_to=[item['verify_email']], subject=subject)
                        elif senior_spotlight_article['status'] == 'failure':
                            logging.error("Failure in processing the article - %s", repr(senior_spotlight_article))
                            utils.send_aws_email(msg_html=json.dumps(senior_spotlight_article, indent=4),
                                                 send_from=customer_config.senior_spotlight_sender_email,
                                                 send_to=emails, subject='Error ' + subject)
                    item['spotlight_article'] = repr(senior_spotlight_article)

                else:
                    raise
            except:
                logging.error('Error processing Senior Spotlight for %s - %ss', repr(item), traceback.format_exc())
            try:
                dynamo.dynamo_put_item(table_name=general_config['processed_senior_spot_light'], entry=item)
                dynamo.dynamo_delete_item(table_name=general_config['senior_spot_light'], keys=['dateAdded'],
                                          vals=[item['dateAdded']])
            except Exception as e:
                logging.error("Error processing %s in to the spotlight dynamo table", repr(item))


def send_report_email(customer_config, today_datetime, articles, stats_details, delete_files=True, posted_urls=None):

    message = '<p>NUMBER OF ARTICLES - %s - %i\n\n\n\n\n\n\n' % (
              customer_config.name, len(articles))

    logging.info(message)

    subject = customer_config.general_config['product_name'] + ' -' + customer_config.name + ' -' + \
              customer_config.general_config['published_status'] + \
     '-' + today_datetime.strftime("%Y-%m-%d") + "(" + customer_config.general_config['system_name'] + ")"

    active_customers_entry = dynamo.dynamo_get_item(table_name=customer_config.general_config['active_customers'],
                                                    keys=['customer_name'], vals=[customer_config.name])
    once_job = False
    if active_customers_entry and 'publishing_frequency' in active_customers_entry and \
            str(active_customers_entry['publishing_frequency']).lower() == 'once':
        once_job = True

    emails = []
    if customer_config.editor_email:
        emails += [customer_config.editor_email]
    if customer_config.publisher_email:
        emails += [customer_config.publisher_email]
    if customer_config.additional_contact_emails_for_articles:
        emails += customer_config.additional_contact_emails_for_articles

    emails = list(set(emails))

    if len(articles) > 0:
        posted_data_frame = DataFrame()
        if customer_config.auto_publish:
            try:
                message += stats.general_stats_info(articles=articles, stats=stats_details)
                posted_data_frame = DataFrame(data=posted_urls)

            except Exception as e:
                logging.error("error converting stats")

        file_names = []

        html_file = str(customer_config.article_output_file).replace(".txt", ".html")
        file_names.append('RAW-HTML-' + str(os.path.basename(customer_config.article_output_file)))
        file_names.append('FINISHED-HTML-' + str(os.path.basename(html_file)))

        file_list = [customer_config.article_output_file, html_file]

        if once_job:
            file_list.pop(0)
            file_names.pop(0)

        posted_data_file = str(customer_config.article_output_file).replace(".txt", ".csv")

        if not posted_data_frame.empty:
            posted_data_frame.to_csv(posted_data_file)
            file_list.append(posted_data_file)
            file_names.append(str(os.path.basename(posted_data_file)))
        # utils.send_mail(message=message, send_from='staconsulting@outlook.com', send_to=emails,
        #                 subject=subject, files=file_list)
        
        message += "</p><br><br><p>We\'ve attached your high school sports reporting export.<br><br>If there's anything we can improve, \
        fix, or need to know about please let us know. Bugs, inaccuracies, grammar errors, and great new ideas... we \
        want to know about them. <a href=\"https://forms.gle/jRcn3pWk5RuB8Hvd9\">Use this form</a> to tell us. We\'ll come back to you with what we find and use your \
        feedback to improve <a href=\"https://www.ledeai.com/\">Lede AI</a>.<br><br>Thanks!<br>All of us at Lede AI</p>"

        utils.send_aws_email(msg_html=message, send_from='content@ledeai.com', send_to=emails,
                             subject=subject, files=file_list, filenames=file_names)
        if delete_files:
            for file_name in file_list:
                if os.path.isfile(file_name):
                    logging.info("deleting file - %s", file_name)
                    os.remove(file_name)

    else:
        # utils.send_mail(message=message, send_from='staconsulting@outlook.com', send_to=emails, subject=subject,
        #                 )
        message += "</p>"
        utils.send_aws_email(msg_html=message, send_from='content@ledeai.com', send_to=emails, subject=subject)


def record_factory_factory(customer_name, article_type, game_id="None"):
    def record_factory(*args, **kwargs):
        record = orig_factory(*args, **kwargs)
        record.customer_name = customer_name
        record.article_type = article_type
        record.game_id=game_id
        return record
    return record_factory

if __name__ == '__main__':

    logging.error("Starting the ai article handler \n")

    try:
        
        message = os.getenv('INPUT_MSG', None)

        if message:
            logging.info("Received the input message - %s", repr(message))
            message = json.loads(message)
            if 'type' in message:

                logging.info("fetching general config")

                general_config = dynamo.dynamo_get_item(table_name=config.GENERAL_CONFIG_TABLE, keys=['key'],
                                                        vals=[config.CONFIG_KEY])

                customer_name = "Default"

                article_type = message['type']

                if 'customer_name' in message:
                    customer_name = message['customer_name']

                logging.setLogRecordFactory(record_factory_factory(customer_name, article_type))

                formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] - [%(customer_name)s] - [%(game_id)s]   %(message)s")
                
                root_handler.setFormatter(formatter)

                fixed_date = None
                if message.get('fixed_date', None):
                    fixed_date = datetime.strptime(message['fixed_date'], "%m-%d-%Y")
                if message['type'] == 'article':
                    only_article_numbers = False
                    if 'publishing_frequency' in message and \
                         str(message['publishing_frequency']).lower() == 'once':
                        if 'article_numbers_only_for_once_job' in general_config and \
                             general_config['article_numbers_only_for_once_job']:
                            only_article_numbers = True
                    process_article_request(customer_name=message['customer_name'],
                                            fixed_date_time=fixed_date,
                                            game_range_days=message.get('game_range', 0),
                                            run_time_id=message.get('app_event_name', 'default'),
                                            article_numbers_only=only_article_numbers,
                                            general_config=general_config)
                elif message['type'] == 'spotlight':
                    process_senior_spotlights(general_config=general_config)

        time.sleep(10)
        logging.info("Completed processing, hence exiting")
        os._exit(2)
    except Exception:
        logging.exception("Error encountered, hence exiting from main code")
        os._exit(1)
