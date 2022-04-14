import json
from db import dynamo
import pandas as pd
import math

def download_article_content():
    table_name = "LEDEAI_CONTENT_STAGE"
    article_keys_to_get = ["headlines", "l2_summary_content", "l3_tie", "l3_winning_losing", "deep_link",
                           "l3_neither_scored", "l2_filler_content", "l3_winning_winning", "deep_link_end_fillers"]

    article_content = {}
    for each_key in article_keys_to_get:
        article_content[each_key] = dynamo.dynamo_get_item(table_name=table_name,
                                                           keys=['content_type'], vals=[each_key])

    print(article_content)

    with (open('tests/data/article_content.json', 'w')) as fp:
        json.dump(article_content, fp, indent=4)

def update_article_content():
    with open('article/article_content.json') as fp:
        content_json = json.load(fp)
    
    deep_link_end_fillers = content_json['deep_link_end_fillers']
    
    table_name = "LEDEAI_CONTENT_STAGE"
    
    
    for each_content in deep_link_end_fillers:
        each_content['content'] = {}
        each_content['content']['en'] = each_content['base_content']
    
    print(deep_link_end_fillers)
    
    dynamo_content = { 'content_type': 'deep_link_end_fillers', 'content': deep_link_end_fillers }
    
    dynamo.dynamo_put_item(table_name=table_name, entry=dynamo_content)

def format_csv_article_dict():
    dynamo_json = []
    with open('/Users/jothipanchatcharam/Documents/LedeAI_Content_revision_2022.csv') as fp:
        df = pd.read_csv(fp)
        df.dropna(how='all', inplace=True)
        df = df.T
        df_dict = df.to_dict()
        transformed_content = {'headline': [],
                                'l2_summary_content': []}
        for each_row_num, each_row in df_dict.items():
            each_row['content_code'] = int(each_row['content_code'])
            each_row['content_scoring_type'] = 'any'
            each_row['content'] = {'en': each_row['base_content']}
            if type(each_row['content_dynamics']) is not str and math.isnan(each_row['content_dynamics']):
                each_row.pop('content_dynamics')
            
            transformed_content[each_row['content_type']].append(each_row)
        dynamo_json.append({'content_type': 'headlines', 'content': transformed_content['headline']})
        dynamo_json.append({'content_type': 'l2_summary_content', 'content': transformed_content['l2_summary_content']})
        print(dynamo_json)

        table_name = 'LEDEAI_CONTENT_STAGE'

        for each_content in dynamo_json:
            dynamo.dynamo_put_item(table_name=table_name, entry=each_content)


format_csv_article_dict()
