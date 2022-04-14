from datetime import datetime
from db import dynamo
import json


def log_in_ddb(asset_id, game_start_time, customer_name, customer_id, post_url,
               game_id, home_team_id, away_team_id, game_url, system_type,squad_id, sport_name, general_config,
               invoice_company='',
               post_response='',post_request='', log_time=None):

    active_customers_entry = dynamo.dynamo_get_item(table_name=general_config['active_customers'],
                                                    keys=['customer_name'], vals=[customer_name])
    once_job = False
    if active_customers_entry and 'publishing_frequency' in active_customers_entry and \
            str(active_customers_entry['publishing_frequency']).lower() == 'once':
        once_job = True

    if general_config['log_in_ddb'] is True and not once_job:
        table_name = general_config['posted_assets_table']

        if log_time is None:
            now = datetime.utcnow().strftime("%Y %m %d %H:%M:%S")
        else:
            now = log_time.strftime("%Y %m %d %H:%M:%S")
        entry = {
            'id': asset_id,
            'invoice_company': invoice_company,
            'game_start_time': game_start_time,
            'log_time': now,
            'customer_name': customer_name,
            'customer_id': customer_id,
            'post_url': post_url,
            'game_id': game_id,
            'home_team_id': home_team_id,
            'away_team_id': away_team_id,
            'game_url': game_url,
            'sport_name': sport_name,
            'squad_id': squad_id,
            'type': system_type,
            'post_response': post_response,
            'post_request': post_request
        }

        return dynamo.dynamo_put_item(entry=entry, table_name=table_name)


def log_in_alt_table(entry, general_config, customer_name=None):

    active_customers_entry = dynamo.dynamo_get_item(table_name=general_config['active_customers'],
                                                    keys=['customer_name'], vals=[customer_name])
    once_job = False
    if active_customers_entry and 'publishing_frequency' in active_customers_entry and \
            str(active_customers_entry['publishing_frequency']).lower() == 'once':
        once_job = True

    if general_config['log_in_ddb'] is True and not once_job:
        table_name = general_config['posted_assets_table_alt']

        return dynamo.dynamo_put_item(table_name=table_name, entry=entry)


def log_in_spotlights(entry, general_config):

    if general_config['log_in_ddb'] is True:
        table_name = general_config['senior_spot_light_posted_assets']

        return dynamo.dynamo_put_item(table_name=table_name, entry=entry)
