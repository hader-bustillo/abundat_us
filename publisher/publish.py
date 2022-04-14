"""
This is the publish module which will have all the necessary interfaces defined through which
we can publish articles . The current options supported are Blox and wordpress.

"""
import requests
import logging
import json
from db import dynamo
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from string import Template
from urllib.parse import quote
from publisher.dynamo_log import log_in_ddb, log_in_alt_table, log_in_spotlights
from copy import deepcopy
from crypt import crypt
import io
logger = logging.getLogger(__name__)


class Blox():

    def __init__(self, article, blox_config, customer_config, spot_lights=False):
        self.article = article
        self.customer_config = customer_config
        self.general_config = self.customer_config.general_config
        self.blox_config = blox_config
        self.html_text = article.html_text
        self.plain_text = article.plain_text if hasattr(article, 'plain_text') else None
        self.headline = self._get_article_headline(article, customer_config)
        self.now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.now_plus_30 = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        self.customer_id = customer_config.id
        self.customer_name = customer_config.name
        self.invoice_company = customer_config.invoice_company if hasattr(customer_config,
                                'invoice_company') else customer_config.name
        self.spot_lights = spot_lights
        self.scorestream_url = None

        if self.spot_lights:
            self.html_img = article.html_img
        if not spot_lights:
            self.sport_name = article.l2_data.game.sport_name
            self.game_id = article.l2_data.game.game_id
            self.gender = article.l2_data.all_game_data.squad_data.gender
            self.home_team_name = article.l2_data.all_game_data.home_team_data.team_name
            self.away_team_name = article.l2_data.all_game_data.away_team_data.team_name
            self.state = article.l2_data.state
            self.home_team_id = article.l2_data.all_game_data.individual_game.home_team_id
            self.away_team_id = article.l2_data.all_game_data.individual_game.away_team_id
            self.game_url = article.l2_data.all_game_data.individual_game.url
            self.both_genders = article.l2_data.all_game_data.sport_details.both_genders

        self.section = self._get_section()


    @staticmethod
    def _get_article_headline(article, customer_config):
        if hasattr(customer_config, 'headline') and customer_config.headline:
            headline = str(customer_config.headline).replace('$date', datetime.now().strftime("%m-%d-%Y"))
            return headline
        else:
            return article.headline

    def create_payload(self, image_link=None):
        # this url config is unique to Richland Source.  This is something that all customers will
        # want a different config set for.

        json_payload = deepcopy(self.blox_config['json_payload_structure'])

        if self.spot_lights:
            json_payload.pop('keywords')
            if image_link:
                json_payload['published'] = True
                json_payload['type'] = 'Image'
                json_payload['content'] = 'headline'

            else:
                json_payload['published'] = self.blox_config['spot_light_published_status']
            json_payload['authors'] = self.customer_name.replace("Local", "Staff")
            json_payload.pop('archive_time')
        for item in json_payload:
            if item == 'id':
                if self.spot_lights:
                    json_payload[item] = self.article.article_id
                    if image_link:
                        json_payload[item] += '_img'
                else:
                    json_payload[item] = json_payload[item].replace("$game_id$", str(self.game_id))
                    json_payload[item] = json_payload[item].replace("$sportname$", self.sport_name)
            elif item == 'keywords' and not self.spot_lights:
                if type(json_payload[item]) is list:
                    for index, key in enumerate(json_payload[item]):
                        if str(key).startswith('#'):
                            prefix = '#'
                            if 'sport_name' in key and self.both_genders:
                                prefix += self.gender
                            json_payload[item][index] = prefix + getattr(self, key[1:])
                        elif str(key).startswith('$'):
                            json_payload[item][index] = str(key).replace("$", "")
                        else:
                            json_payload[item][index] = getattr(self, key)
                        # json_payload[item][index] = str(json_payload[item][index]).replace(" ", "")
                else:
                    logging.info("Yet to implement keyword replacement for type"+type(json_payload[item]))
            elif item == 'start_time':
                json_payload[item] = self.now
            elif item == 'archive_time':
                json_payload[item] = self.now_plus_30
            elif item == 'title':
                if self.spot_lights and image_link:
                    json_payload[item] = self.article.article_id + '_img'
                else:
                    json_payload[item] = '<b>' + self.headline +  '</b>'
            elif item in ['content']:
                json_payload[item] = getattr(self, json_payload[item])
            elif item == 'sections':
                json_payload[item] = self.section

        if self.spot_lights:
            entry = json_payload
        else:
            entry = self.apply_specific_changes(json_payload)
        return entry

    def apply_specific_changes(self, entry):

        changes = dynamo.dynamo_get_item(keys=['id'], table_name='CONTENT_FOR_UNIQUE_TAG',
                                         vals=['game_%i'%self.game_id])
        logging.info(changes)
        if type(changes) != dict: return entry
        # this is the message that is returned in the case of a no records being found
        else:
            change = changes['change']
            for key in change:
                if type(change[key]) is dict:
                    # if the value of the change[key] is a dictionary (aka metadata), we append whatever the
                    # current value is to what the new metadata is
                    for k in change.keys():
                        if k in entry.keys():
                            val = entry[k] + change[k]
                            entry[k] = val
                        else:
                            entry[k] = change[k]
                            # if the value of change[key] we are adding that to entry,
                            # so it's just key = value, no appending.

                else:
                    entry[key] = change[key]
                    # if the value is a string/int/whatever we simply replace.
                    # This means that if someone wanted to replace the content they could, but I don't see
                    # anyone going in and ever wanting to preemptively append content to a yet-to-be-written article.
        return entry

    def _get_section(self):
        if self.spot_lights:
            return 'senior_spotlights'
        if 'sections' in self.blox_config['json_payload_structure']:
            if type(self.blox_config['json_payload_structure']['sections']) is list:
                # find the right sport config section
                section = self.blox_config['json_payload_structure']['sections']
                section_config = list(filter(lambda config: self.sport_name in config['sport_name'] or
                                             'all' in config['sport_name'], section))[0]
                return self.construct_section(section_config)
            else:
                logging.info("In th string part of sections")
                section = self.blox_config['json_payload_structure']['sections']
                logging.info("section before replacement %s", str(section))
                section = str(section).replace("$sportname", self.sport_name).replace("$gender", self.gender)
                logging.info("section before replacement %s", str(section))
                return section

    def construct_section(self, section_config):
        section = ""
        if 'id_prefix' in section_config and section_config['id_prefix'] is not None:
            section += section_config['id_prefix']
            section += "/"
        if 'gender' in section_config and section_config['gender'] is True:
            section += self.gender
            section += '_'
        if 'sport' in section_config and section_config['sport'] is True:
            section += self.sport_name + "/"
        if 'id_suffix' in section_config and section_config['id_suffix'] is not None:
            section += section_config['id_suffix']

        return [section]

    def post_asset(self, payload:dict, url, image=False):
        post_url = url['post_url']
        webservice_key = crypt.decrypt_string(url['webservice_key'])
        webservice_pswd = crypt.decrypt_string(url['webservice_password'])

        auth = HTTPBasicAuth(webservice_key, webservice_pswd)

        logging.info("the payload created for BLOX is %s", repr(payload))

        if image:

            try:
                json_payload_file = io.BytesIO(json.dumps(payload).encode('utf-8'))
            except Exception as e:
                logging.error(e)
            response_content = requests.get(self.html_img).content

            logging.info("type of json payload -%s  and image resp content - %s", repr(type(json_payload_file)),
                                                                                       repr(type(response_content)))
            files = {'image': response_content,
                     'metadata': json_payload_file}
            post_request = requests.post(files=files, auth=auth, url=post_url)
        else:
            post_request = requests.post(json=payload,url=post_url, auth=auth)

        logging.info("Received a %d status code with response %s", post_request.status_code, post_request.json())

        asset_id_json = post_request.json()

        if post_request.status_code == 201 and not image:

            if 'internalid' in asset_id_json:
                asset_id = asset_id_json['internalid']
                game_post_url = self._get_post_url(asset_id=asset_id, url=url)

                if self.spot_lights:

                    entry = {
                        'article_id': self.article.article_id,
                        'posted_url': game_post_url,
                        'content': self.html_text,
                        'datetime': self.now
                    }
                    log_in_spotlights(entry=entry)
                else:
                    if hasattr(self.customer_config, 'logstarttime') and self.customer_config.logstarttime is True:
                        log_time = self.article.l2_data.all_game_data.individual_game.start_date_time
                    else:
                        log_time = None

                    ddb_id = self.customer_name + '_' + str(self.home_team_id) + '_' + \
                        str(self.article.l2_data.all_game_data.individual_game.home_squad_id) + '_' \
                        + self.article.l2_data.all_game_data.individual_game.sport_name + '_' + 'blox'

                    ddb_alt_id = self.customer_name + '_' + str(self.away_team_id) + '_' + \
                        str(self.article.l2_data.all_game_data.individual_game.home_squad_id) + '_' \
                        + self.article.l2_data.all_game_data.individual_game.sport_name + '_' + 'blox'

                    game_start_time = self.article.l2_data.all_game_data.individual_game.utc_start_date_time

                    log_in_ddb(asset_id=ddb_id, customer_name=self.customer_name,
                               game_start_time= game_start_time,
                               squad_id=str(self.article.l2_data.all_game_data.individual_game.home_squad_id),
                               sport_name=self.article.l2_data.all_game_data.individual_game.sport_name,
                               customer_id=self.customer_id,post_url=game_post_url,
                               game_id=self.game_id,home_team_id=self.home_team_id,
                               away_team_id=self.away_team_id, game_url=self.game_url,system_type='blox',
                               invoice_company=self.invoice_company,post_request=repr(payload),
                               post_response=repr(asset_id_json),
                               log_time=log_time, general_config=self.general_config)

                    entry = {
                        'id': ddb_alt_id,
                        'alt_id': ddb_id,
                        'game_start_time': game_start_time
                    }

                    log_in_alt_table(entry=entry, customer_name=self.customer_name, general_config=self.general_config)

                logging.info('Article Logged with id for BLOX %s' % asset_id)

                if game_post_url and not self.spot_lights:
                    self.scorestream_url = quote(game_post_url, safe=':/?=&')
        return post_request.status_code

    @staticmethod
    def _get_post_url(url, asset_id):
        get_url = url['get_url']
        auth = HTTPBasicAuth(crypt.decrypt_string(url['webservice_key']),
                             crypt.decrypt_string(url['webservice_password']))
        get_response = requests.get(url=get_url, auth=auth, params={'id': asset_id}).json()
        logging.info("the get response from blox is %s", repr(get_response))
        post_url = get_response['url'] if 'url' in get_response else ""
        return post_url


class WordPress:
    def __init__(self, article, word_press_config, customer_config, wp_session:dict):
        self.word_press_config = word_press_config
        self.general_config = customer_config.general_config
        self.system_name = word_press_config['system_name']
        self.sport_name = article.l2_data.game.sport_name
        self.gender = article.l2_data.all_game_data.squad_data.gender
        self.category = self._get_categories()
        self.game_id = article.l2_data.game.game_id
        self.content = article.html_text
        self.title = self._get_article_headline(article, customer_config)
        self.excerpt = article.headline
        self.now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.home_team_name = article.l2_data.all_game_data.home_team_data.team_name
        self.away_team_name = article.l2_data.all_game_data.away_team_data.team_name
        self.state = article.l2_data.state
        self.customer_name = customer_config.name
        self.customer_id = customer_config.id
        self.game_day = str(article.l2_data.all_game_data.individual_game.game_day) + \
            str(article.l2_data.all_game_data.individual_game.game_month)
        self.status = word_press_config['publishing_status']
        self.type = word_press_config['publishing_type'] if 'publishing_type' in word_press_config else None
        self.article = article
        self.wp_session = wp_session['wp_session']
        self.wp_url = self.word_press_config['wp_url']
        self.wp_headers = self.word_press_config['headers']
        self.wp_headers['X-WP-Nonce'] = wp_session['wp_nonce']
        self.scorestream_url = None
        self.invoice_company = customer_config.invoice_company if hasattr(customer_config,
                                                                          'invoice_company') else customer_config.name
        self.winning_team_name = article.l2_data.winning_team_name
        self.losing_team_name = article.l2_data.losing_team_name
        self.winning_team_score = article.l2_data.winning_team_score
        self.losing_team_score = article.l2_data.losing_team_score
        self.customer_config = customer_config


    @staticmethod
    def _get_article_headline(article, customer_config):
        if hasattr(customer_config,'headline') and customer_config.headline:
            headline = str(customer_config.headline).replace('$date', datetime.now().strftime("%m-%d-%Y"))
            return headline
        else:
            return article.headline

    def create_payload(self):
        # this url config is unique to Richland Source.  This is something that all customers will
        # want a different config set for.
        payload = deepcopy(self.word_press_config['data'])

        for item in payload:
            if item == 'slug':
                obj_id = Template(payload[item])
                payload[item] = obj_id.safe_substitute(date=self.game_day, game_id=self.game_id)
            elif item == 'tags' or item == 'categories':
                if type(payload[item]) is list:
                    payload_item = []
                    for key in payload[item]:
                        replaced_item = getattr(self, key).replace("$sportname", self.sport_name).replace("$gender", self.gender)
                        logging.info("Replaced item is " + repr(replaced_item) + "for" + getattr(self, key))
                        payload_item.append(replaced_item)
                    payload[item] = self.get_ids(item_list=payload_item, endpoint=item)
                else:
                    logging.info("Yet to implement keyword replacement for type"+type(payload[item]))

            elif item == 'meta':
                if type(payload[item]) is dict:
                    payload[item] = {key: getattr(self, value) for (key, value) in payload[item].items()}
                    logging.info("The transformed meta dict is %s", repr(payload[item]))
                else:
                    logging.info("yet to implement %s representation for meta", type(payload[item]))
            else:
                payload[item] = getattr(self, item)
        return payload

    def post_asset(self, payload):
        try:
            return_code = True
            if 'slug' in payload:
                return_code = self.check_post_exists(payload['slug'])

            if return_code:
                rc = self.wp_session.post(url=self.wp_url + self.word_press_config['post_endpoint'],
                                          data=json.dumps(payload),
                                          headers=self.wp_headers,
                                          verify=False)
                if rc.status_code == 201:
                    post_url = rc.json()['guid']['rendered']
                    asset_id = rc.json()['id']
                    self.scorestream_url = post_url

                    if hasattr(self.customer_config, 'logstarttime') and self.customer_config.logstarttime is True:
                        log_time = self.article.l2_data.all_game_data.individual_game.start_date_time
                    else:
                        log_time = None

                    ddb_id = self.customer_name + '_' + \
                             str(self.article.l2_data.all_game_data.individual_game.home_team_id) + '_' + \
                             str(self.article.l2_data.all_game_data.individual_game.home_squad_id) + '_' \
                             + self.sport_name + '_' + self.system_name

                    game_start_time = self.article.l2_data.all_game_data.individual_game.utc_start_date_time

                    ddb_alt_id = self.customer_name + '_' + \
                             str(self.article.l2_data.all_game_data.individual_game.away_team_id) + '_' + \
                             str(self.article.l2_data.all_game_data.individual_game.home_squad_id) + '_' \
                             + self.sport_name + '_' + self.system_name

                    log_in_ddb(asset_id=ddb_id,
                               game_start_time=game_start_time,
                               sport_name=self.sport_name,
                               squad_id=str(self.article.l2_data.all_game_data.individual_game.home_squad_id),
                               customer_name=self.customer_name,
                               customer_id=self.customer_id,post_url=post_url,
                               game_id=self.game_id,
                               home_team_id=self.article.l2_data.all_game_data.individual_game.home_team_id,
                               away_team_id=self.article.l2_data.all_game_data.individual_game.away_team_id,
                               game_url=self.article.l2_data.all_game_data.individual_game.url,
                               system_type=self.system_name,
                               invoice_company=self.invoice_company,
                               post_request=repr(payload),
                               post_response=repr(rc.json()),
                               log_time=log_time, general_config = self.general_config)

                    entry = {
                        'id': ddb_alt_id,
                        'alt_id': ddb_id,
                        'game_start_time': game_start_time
                    }

                    log_in_alt_table(entry=entry, customer_name=self.customer_name, general_config=self.general_config)

                    logging.info("The return code from wordpress api is %d", rc.status_code)

                    return rc.status_code
                else:
                    logging.info("Error ouccred during pubishing - %s", repr(rc))
                    if rc.status_code:
                        return rc.status_code
                    else:
                        return 999
            else:
                logging.info("the posts already exists in the posted table")
                return 409

        except Exception as e:
            logging.error("Exception occurred during wordpres publish" + str(e))

    def get_ids(self, item_list, endpoint):
        new_item_list = []
        for item in item_list:
            try:
                resp = self.wp_session.get(url=self.wp_url + endpoint + "?search=" + item)
                resp_json = self.filter_resp(resp, item)
                if resp.status_code == 200 and resp_json:
                    item_id = self.process_get_response(resp=resp_json)
                    logging.info("Successfully retrieved id %d for %s", item_id, item)
                else:
                    logging.info("Tag item %s does not exist", item)
                    logging.info("Creating New tag")
                    data = {"name": item}
                    resp = self.wp_session.post(url=self.wp_url + endpoint,
                                                data=json.dumps(data),
                                                headers=self.wp_headers)
                    logging.info("The response received is %s", resp.text)
                    if resp.status_code == 201:
                        item_id = self.process_post_response(resp=resp)
                        logging.info("Successfully created id %d for %s", item_id, item)
                    elif 'term_exists' in resp.text:
                        term_resp = json.loads(resp.text)
                        if 'data' in term_resp and 'term_id' in term_resp['data']:
                            item_id = int(term_resp['data']['term_id'])
                            logging.info("Successfully created id %d for %s", item_id, item)
                        else:
                            logging.info("Error creating the tag for item %s", item)
                            continue
                    else:
                        logging.info("Error creating the tag for item %s", item)
                        continue
                new_item_list.append(item_id)
            except Exception as e:
                logging.error("Exception occurred during wordpres publish for creating tags" + str(e))
        return new_item_list

    @staticmethod
    def filter_resp(resp, item):
        resp_json = []
        if resp.status_code == 200:
            json_resp = json.loads(resp.text)
            resp_json = list(filter(lambda x: str(x['name']).lower() == str(item).lower(), json_resp))
        return resp_json

    @staticmethod
    def process_get_response(resp):
        item_id = resp[0]['id']
        return item_id

    @staticmethod
    def process_post_response(resp):
        logging.info("The return code from wordpress api is %d", resp.status_code)
        json_resp = json.loads(resp.text)
        item_id = json_resp['id']
        return item_id

    def check_post_exists(self, slug):
        resp = self.wp_session.get(url=self.wp_url + "posts?slug=" + slug)
        logging.info("response for slug" + str(slug) + resp.text)

        if self._entry_exists_in_assets_table():
            logging.info("Entry exists for game_id - %d exists for %s in posted assets", self.game_id, self.customer_name)
            return False
        elif resp.text != '[]':
            logging.info("Post with slug %s does exist, skipping reposting", slug)
            return False
        else:
            logging.info("Post with slug %s does not exist", slug)
            return True

    def _entry_exists_in_assets_table(self):
        table_name = self.general_config['posted_assets_table']

        ddb_id = self.customer_name + '_' + \
                 str(self.article.l2_data.all_game_data.individual_game.home_team_id) + '_' + \
                 str(self.article.l2_data.all_game_data.individual_game.home_squad_id) + '_' \
                 + self.sport_name + '_' + self.system_name

        game_start_time = self.article.l2_data.all_game_data.individual_game.utc_start_date_time

        posts = dynamo.dynamo_get_item(table_name=table_name,keys=['id', 'game_start_time'],
                                       vals=[ddb_id, game_start_time])

        logging.info("Checking in posted assets table for %s-%s", ddb_id, game_start_time)

        if posts:
            logging.info("The posts entry found for %d and %s", self.game_id, self.customer_name)
            return True
        else:
            return False

    def _get_categories(self):
        if 'categories' in self.word_press_config and \
                type(self.word_press_config['categories']) is dict:
            # find the right sport config section
            section = self.word_press_config['categories'][self.sport_name] if self.sport_name in \
                                                                          self.word_press_config['categories'] else \
                                                                          self.word_press_config['categories']['all']

            return section







