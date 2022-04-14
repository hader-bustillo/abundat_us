"""
Provides the actual wrapper function for publishing or writing articles.
Current options are Blox, Wordpress and Writing to a file.

"""
import datetime
import logging
from publisher import publish
from scorestream import ss_integration
import schedule
import requests
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from threading import Lock
from requests.auth import HTTPBasicAuth
from crypt import crypt
import io
from s3 import s3
from pandas import DataFrame

selenium_lock = Lock()

logger = logging.getLogger(__name__)


class HandlePublish:

    def __init__(self, customer_config, spot_lights=False):
        self.customer_config = customer_config
        self.general_config = self.customer_config.general_config
        self.spot_lights = spot_lights
        self.stats = {}
        self.scorestream_urls = {}
        self.wp_session_info = {}
        self.postback_urls = []

    def publish_articles(self, article):
        if self.customer_config.auto_publish is True:
            logging.info("Auto publish is set to true\n")
            for system in self.customer_config.publishing_system:
                if system['system_type'] == 'blox' and system['active']:
                    logging.info("Auto publishing through BLOX\n")
                    self.send_to_blox(article=article, system=system)
                if system['system_type'] == 'wordpress' and system['active']:
                    logging.info("Auto publishing through wordpress\n")
                    self.send_to_wordpress(article=article, system=system)

    def send_to_wordpress(self, article, system):
        try:
            if not self.wp_session_info:
                self.__get_wp_session(wordpress_config=system)

            wp = publish.WordPress(article=article,word_press_config=system,
                                   customer_config=self.customer_config, wp_session=self.wp_session_info)
            payload = wp.create_payload()

            logging.info("The wordpress payload created is %s", repr(payload))

            rc = wp.post_asset(payload)

            self._append_stats(rc, system['system_name'])

            if wp.scorestream_url and 'scorestream_postback' in system \
                    and system['scorestream_postback']:
                if system['system_name'] not in self.scorestream_urls:
                    self._init_scorestream_urls(system)
                self._create_score_stream_urls(system_name=system['system_name'],
                                               game_id=wp.game_id,
                                               postback_url=wp.scorestream_url)
            self._create_post_back_urls(system=system, game_id=wp.game_id, postback_url=wp.scorestream_url)
        except Exception as e:
            self._append_stats("999", system['system_name'])
            logging.error("the error occured " + repr(e))
            pass

    def send_to_blox(self, article, system):
        try:
            blox = publish.Blox(article=article, blox_config=system,
                                customer_config=self.customer_config,
                                spot_lights=self.spot_lights)
            if self.spot_lights:
                payload = blox.create_payload(image_link=True)
                rc = blox.post_asset(payload=payload, url=system['urls'], image=True)

                logging.info("the return code from blox image creation is %s", repr(rc))
                img_id = payload['id']
                relationship_dict = {'id': img_id, 'type': "child", 'app': 'editorial'}
                blox.blox_config['json_payload_structure']['relationships'] = []
                blox.blox_config['json_payload_structure']['relationships'].append(relationship_dict)

                logging.info("the json payload struct created is %s", repr(blox.blox_config['json_payload_structure']))
            payload = blox.create_payload()

            logging.info("The blox payload created is %s", repr(payload))

            rc = blox.post_asset(payload=payload, url=system['urls'])
            self._append_stats(rc, system['system_name'])

            if blox.scorestream_url and 'scorestream_postback' in system \
                    and system['scorestream_postback']:
                if system['system_name'] not in self.scorestream_urls:
                    self._init_scorestream_urls(system)
                self._create_score_stream_urls(system_name=system['system_name'],
                                               game_id=blox.game_id,
                                               postback_url=blox.scorestream_url)
            self._create_post_back_urls(system=system, game_id=blox.game_id, postback_url=blox.scorestream_url)
        except Exception as e:
            self._append_stats("999", system['system_name'])
            logging.error("the error occured " + repr(e))

    @staticmethod
    def send_to_scorestream(scorestream_urls):
        for item in scorestream_urls:
            ss_integration.post_games_posts_add(game_id=item['game_id'],
                                                postback_text=item['postback_url'])
        logging.info("Completed posting back to scorestream\n")
        return schedule.CancelJob

    def write_to_file(self, article_in_files, run_time_id, current_datetime=datetime.datetime.now(),
                      article_run_detailed_info=[]):
        logging.info("preparing to write the articles in to the file")
        st = ''
        html_file_name = self.customer_config.article_output_file.replace('.txt', '.html')

        if article_in_files['new_games']:
            st += '<h1>New Games</h1>'
            st += article_in_files['new_games']
        if article_in_files['old_games']:
            st += '<h1>Old Games</h1>'
            st += article_in_files['old_games']

        general_config = self.general_config
        s3_bucket = general_config['article_s3_bucket']

        text_file_buf = io.BytesIO(bytes(st, encoding='utf-8'))
        html_file_buf = io.BytesIO(bytes(st, encoding='utf-8'))
        csv_file_buf = io.StringIO()

        article_run_detailed_info_csv = DataFrame(data=article_run_detailed_info)
        article_run_detailed_info_csv.to_csv(csv_file_buf)
        csv_file_buf.seek(0)

        csv_value = csv_file_buf.getvalue()

        csv_file_buf = io.BytesIO(bytes(csv_value, encoding='utf-8'))
        csv_file_buf.seek(0)
        current_date = current_datetime.strftime("%Y-%m-%d")
        current_time = current_datetime.strftime("%H-%M")
        text_file_s3_key = os.path.join(self.customer_config.name, current_date, current_time, run_time_id + '.txt')
        html_file_s3_key = os.path.join(self.customer_config.name, current_date, current_time, run_time_id + '.html')
        csv_file_s3_key = os.path.join(self.customer_config.name, current_date, current_time, run_time_id + '.csv')

        txt_s3_url = s3.upload_to_aws(s3_bucket=s3_bucket, file_data=text_file_buf, s3_key=text_file_s3_key)
        html_s3_url = s3.upload_to_aws(s3_bucket=s3_bucket, file_data=html_file_buf, s3_key=html_file_s3_key)
        csv_s3_url = s3.upload_to_aws(s3_bucket=s3_bucket, file_data=csv_file_buf, s3_key=csv_file_s3_key,
                         extra_args={'ACL': 'public-read'})

        self.customer_config.html_file_s3_key = html_file_s3_key
        self.customer_config.text_file_s3_key = text_file_s3_key

        with open(self.customer_config.article_output_file, 'w+') as tf:
            tf.write(st)
        with open(html_file_name, 'w+') as tf:
            tf.write(st)

        logging.info("Completed writing the articles in to the file")

        return txt_s3_url, html_s3_url, csv_s3_url

    def get_stats(self):
        return self.stats

    def get_scorestream_urls(self):
        return self.scorestream_urls

    def get_posted_urls(self):
        return self.postback_urls

    def __get_wp_session(self, wordpress_config):
        try:
            selenium_lock.acquire()
            logging.info("Acquired selenium lock")
            selenium_config = self.general_config['selenium']

            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--headless')
            chrome_options.binary_location = selenium_config['binary_path']

            while True:
                if self._check_chrome_process_running():
                    logging.error('Chrome process is already running')
                    time.sleep(15)
                else:
                    logging.error("No more ")
                    break

            if selenium_config['driver_path']:

                driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=selenium_config['driver_path'])
            else:
                driver = webdriver.Chrome(chrome_options=chrome_options)

            driver.get(wordpress_config['wp_logon_url'])

            # find the required elements
            for i in range(3):
                driver.switch_to.default_content()
                user_login = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'user_login')))
                user_login.send_keys(crypt.decrypt_string(wordpress_config['wp_user']))
                time.sleep(3)
                user_pass = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'user_pass')))
                user_pass.clear()
                driver.execute_script("arguments[0].value = arguments[1]", user_pass,
                                      crypt.decrypt_string(wordpress_config['wp_pwd']))
                #        user_pass.send_keys(password)
                time.sleep(17)
                logging.info("sent the user name and password\n")

                wp_submit = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'loginform')))
                logging.info("found the wp-submit\n")
                wp_submit.submit()
                time.sleep(10)
                if 'ERROR' in driver.page_source or 'login_error' in driver.page_source:
                    continue
                else:
                    break

            self._populate_wp_session(driver=driver,
                                      wp_config=wordpress_config)

            driver.stop_client()
            driver.close()
            driver.quit()

        except (AttributeError, KeyError) as e:
            driver.stop_client()
            driver.close()
            driver.quit()
            logging.error("exception encountered during login through selenium %s", repr(e))
            raise
        finally:
            selenium_lock.release()
            logging.info("released selenium lock")

    def _populate_wp_session(self, driver, wp_config):
        try:
            wp_session = requests.Session()
            wp_session.cookies.clear()
            wp_cookies = driver.get_cookies()

            c = [wp_session.cookies.set(c['name'], c['value']) for c in wp_cookies]

            if 'wpApiSettings' in driver.page_source:
                api_settings = driver.execute_script("return wpApiSettings;")
                logging.info("found wpapi settings variable")
                self.wp_session_info = {
                    'wp_session': wp_session,
                    'wp_nonce': api_settings['nonce']
                }
            elif "data-nonce" in driver.page_source:
                resp = driver.page_source
                wp_nonce = resp.split("data-nonce=\"")[1].split('\"')[0]
                logging.info("found data-nonce")
                self.wp_session_info = {
                    'wp_session': wp_session,
                    'wp_nonce': wp_nonce
                }
            else:
                logging.error("could not find rest settings, hence raise ")
                logging.error("response received is %s", repr(driver.page_source))
                raise

        except Exception as e:
            logging.error("login to the site %s unsuccessful", wp_config['wp_logon_url'])
            logging.error("the response received on the page is %s", repr(driver.page_source))
            raise

        finally:
            self.wp_session_info['system'] = wp_config

    def _create_score_stream_urls(self, system_name, game_id, postback_url):
        if postback_url:
            self.scorestream_urls[system_name]['urls'].append(
                                    {
                                            'game_id': game_id,
                                            'postback_url': postback_url
                                    })

    def _init_scorestream_urls(self, system):
        system_name = system['system_name']
        dft_ss_delay = self._get_score_stream_defualt_time()
        self.scorestream_urls[system_name] = {}
        self.scorestream_urls[system_name]['urls'] = []
        self.scorestream_urls[system_name]['postback_time'] = system['scorestream_delay'] if 'scorestream_delay' \
                                                            in system else dft_ss_delay

    def _create_post_back_urls(self, system, game_id, postback_url):
        system_name = system['system_name']
        self.postback_urls.append({
            'game_id': game_id,
            'postback_url': postback_url,
            'system_type': system_name
        })

    def _get_score_stream_defualt_time(self):
        try:
            score_stream_pb_delay = self.general_config['scorestream_delay']
            return score_stream_pb_delay
        except Exception :
            logging.error("Error obtaining the scorestream config")

    def _append_stats(self,rc, system_name):
        if system_name not in self.stats:
            self.stats[system_name] = {}
        if rc not in self.stats[system_name]:
            self.stats[system_name][rc] = 0
        self.stats[system_name][rc] += 1

    @staticmethod
    def _check_chrome_process_running():
        out = os.popen("ps -aef | grep -i 'chromedriver' | grep -v 'grep'")
        output = out.read()
        if output is None or output == "":
            return False
        else:
            return True

    def logoff_from_wordpress(self):
        try:
            if self.wp_session_info:
                log_out_url= self.wp_session_info['system']['wp_logon_url'] + \
                             '?action=logout&_wpnonce=%s&context=masterbar' % self.wp_session_info['wp_nonce']
                rc = self.wp_session_info['wp_session'].get(url=log_out_url)
                logging.info("logging out from website %s", log_out_url)
            else:
                logging.error("Wp session for %s not found", repr(self.wp_session_info['system']))
        except Exception as e:
            logging.error("Error while logging out of %s", repr(self.wp_session_info['system']))

    def _delete_from_wordpress(self,asset_id,system):
        try:
            if not self.wp_session_info:
                self.__get_wp_session(wordpress_config=system)
            wp_headers = system['headers']
            wp_headers['X-WP-Nonce'] = self.wp_session_info['wp_nonce']
            rc = self.wp_session_info['wp_session'].delete(url=system['wp_url'] + "posts/" + asset_id,
                                                        verify=False, headers=wp_headers)
            logging.info("the response received on delete is %s", repr(rc))
            self.logoff_from_wordpress()
        except Exception as e:
            logging.info("encoruntered exception %s during deletion of asset")

    def _delete_from_blox(self,asset_id,url):
        auth = HTTPBasicAuth(url['webservice_key'], url['webservice_password'])
        delete_body = {'id': asset_id, 'is_internal': True}
        delete_url = str(url['post_url']).replace('create_asset', 'delete_asset')
        delete_response = requests.post(url=delete_url, auth=auth, params=delete_body)
        logging.info("the delete response from blox is %s", repr(delete_response))
        return



