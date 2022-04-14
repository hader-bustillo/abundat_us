"""
This module contains all the methods that will interact with the dynamo DB.
"""
import boto3
from utils import utils
from dynamodb_json import json_util as json
import logging
import decimal


logger = logging.getLogger(__name__)


def float_to_decimal(item):
    if isinstance(item, dict):
        for e in item:
            item[e] = float_to_decimal(item[e])
    if isinstance(item, float):
        item = decimal.Decimal(str(item))
    if isinstance(item, list):
        for i, entry in enumerate(item):
            item[i] = float_to_decimal(entry)
    return item


def dynamo_scan_table(table_name, keys, vals, operators, is_and=None):
    """
    operators are str with val >,<,>=,<=,=
    operators is [str] with options [eq,gt,ls,gte,lse,between,contains,begins_with,ne,is_in] ##NOT CURRENT
    between value must be (small,large)
    keys are db keys, values are scan vals
    max count = 2
    """
    exp = ''
    eav = {}
    op = 'AND '
    new_ops = operators
    
    ret_arr = []
    
    type_dict = {
        int: 'N',
        str: 'S',
        bool: 'BOOL',
        float: 'DECIMAL'
    }
    
    op_dict = {
        'eq' : '=',
        'gt' : '>',
        'gte' : '>=',
        'lt' : '<',
        'lte' : '<=',
    }
    
    vals = float_to_decimal(vals)

    if is_and is False:
        op = 'OR '
    elif is_and is True:
        op = 'AND '

    for i in range(0, len(new_ops)):
        if new_ops[i] in op_dict.keys():
            new_ops[i] = op_dict[new_ops[i]]

    add_op = False
    for i, (key, val, opr) in enumerate(zip(keys, vals, new_ops)):
        if add_op:
            exp += op
        exp += '%s %s :%s ' % (key, opr, str(i))
        eav[':%s' % str(i)] = {str(type_dict[type(val)]): str(val)}
        add_op = True

        if is_and is None:
            break
    return dynamo_scan_table_with_filter(table_name=table_name, filter_expression=exp, expression_value=eav)


def dynamo_query_table_with_filter(table_name, keycondition_expression, filter_expression=None):

    ret_arr = []

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    if filter_expression:
        ret_arr = table.query(KeyConditionExpression=keycondition_expression, FilterExpression=filter_expression)
    else:
        ret_arr = table.query(KeyConditionExpression=keycondition_expression)

    return handle_response(func_name='dynamo_query_table(2)', response=ret_arr['Items'])


def dynamo_query_index(table_name, index_name , keys, vals, operators):
    exp = ''
    eav = {}
    op = 'AND '
    new_ops = operators

    ret_arr = []

    type_dict = {
        int: 'N',
        str: 'S',
        bool: 'BOOL',
        float: 'DECIMAL'
    }

    op_dict = {
        'eq': '=',
        'gt': '>',
        'gte': '>=',
        'lt': '<',
        'lte': '<=',
    }



    vals = float_to_decimal(vals)

    for i in range(0, len(new_ops)):
        if new_ops[i] in op_dict.keys():
            new_ops[i] = op_dict[new_ops[i]]

    add_op = False
    for i, (key, val, opr) in enumerate(zip(keys, vals, new_ops)):
        if add_op:
            exp += op
        if str(opr).lower() == 'between':
            exp += '%s %s :%s AND :%s' % (key, opr, str(i)+'a', str(i)+'b')
            eav[':%s' % str(i) + 'a'] = {str(type_dict[type(val[0])]): str(val[0])}
            eav[':%s' % str(i) + 'b'] = {str(type_dict[type(val[1])]): str(val[1])}
        else:
            exp += '%s %s :%s ' % (key, opr, str(i))
            eav[':%s' % str(i)] = {str(type_dict[type(val)]): str(val)}

        add_op = True

    client = boto3.client('dynamodb')
    paginator = client.get_paginator('query')
    operation_parameters = {
        'TableName': table_name,
        'IndexName': index_name,
        'KeyConditionExpression': exp,
        'ExpressionAttributeValues': eav
    }
    page_iterator = paginator.paginate(**operation_parameters)

    for page in page_iterator:
        for item in page['Items']:
            g = json.loads(item)
            ret_arr.append(g)

    return handle_response(func_name='dynamo_scan_table(2)', response=ret_arr)


def dynamo_put_item(table_name, entry):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    table.put_item(
        Item=removeEmptyString(float_to_decimal(entry))
    )
    return True


def dynamo_delete_item(table_name, keys, vals):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    Key = {}

    if len(keys) != len(vals):
        logger.error("len of keys not equal to len of vals")
        return False

    for i in range(len(keys)):
        Key[keys[i]] = float_to_decimal(vals[i])

    table.delete_item(Key=Key)
    return True


def dynamo_update_item(table_name, key, update_expr, expr_attribute):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    table.update_item(
        Key=key,
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_attribute,
        ReturnValues="UPDATED_NEW"
    )
    return True

def dynamo_batch_put_item(table_name, entry):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    d = utils.de_dup_list(entry)

    try:
        with table.batch_writer() as batch:
            for item in d:
                item = utils.check_dict_for_empty_string(item)
                batch.put_item(
                    Item=removeEmptyString(float_to_decimal(item))
                )
    except:
        logging.exception("Encountered exception uploading items through batch writer")
        logger.info("the list contains duplicates" + repr(d))
        logging.info("trying to upload item by item through dynamo upload")

        for item in d:
            dynamo_put_item(table_name=table_name, entry=item)



def dynamo_scan_table_with_filter(table_name, filter_expression, expression_value):
    ret_arr = []

    client = boto3.client('dynamodb')
    paginator = client.get_paginator('scan')
    operation_parameters = {
        'TableName': table_name,
        'FilterExpression': filter_expression,
        'ExpressionAttributeValues': expression_value
    }
    page_iterator = paginator.paginate(**operation_parameters)

    for page in page_iterator:
        for game in page['Items']:
            g = json.loads(game)
            ret_arr.append(g)

    return handle_response(func_name='dynamo_scan_table(2)', response=ret_arr)

def dynamo_get_item(table_name, keys, vals):
    '''
    keys are [arr] of db table keys, vals are the specific vals we want.
    '''
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    Key = {}
    
    if len(keys) != len(vals):
        logger.error("len of keys not equal to len of vals")
        return False

    for i in range(len(keys)):
        Key[keys[i]] = float_to_decimal(vals[i])

    response = decimal_to_float(table.get_item(Key=Key))
    
    return handle_response(key='Item', response=response, func_name='dynamo_get_item')


def handle_response(response,func_name,key=None):
    if key is None:
        return replaceEmptyString(decimal_to_float(response))
    elif key in response and len(response[key]) > 0:
        return replaceEmptyString(decimal_to_float(response[key]))
    elif key not in response:
        return None
    elif len(response[key]) == 0:
        return None
    elif response['ResponseMetadata']['HTTPStatusCode'] != 200:
        logging.exception("some problem occured with AWS dynamo db operation")
        return None
    else:
        return None


def removeEmptyString(dic):
    if isinstance(dic, dict):
        for e in dic:
            dic[e] = removeEmptyString(dic[e])
    if isinstance(dic, str) and not dic:
        dic = "EMPTY_STRING"
    if isinstance(dic, list):
        for i, entry in enumerate(dic):
            dic[i] = removeEmptyString(entry)
    return dic


def replaceEmptyString(dic):
    if isinstance(dic, dict):
        for e in dic:
            dic[e] = replaceEmptyString(dic[e])
    if isinstance(dic, str) and dic == "EMPTY_STRING":
        dic = ""
    if isinstance(dic, list):
        for i, entry in enumerate(dic):
            dic[i] = replaceEmptyString(entry)
    return dic


def decimal_to_float(item):
    if isinstance(item, dict):
        for e in item:
            item[e] = decimal_to_float(item[e])
    if isinstance(item, decimal.Decimal):
        if item % 1 == 0:
            item = int(item)
        else:
            item = float(item)
    if isinstance(item, list):
        for i, entry in enumerate(item):
            item[i] = decimal_to_float(entry)
    return item




def dynamo_db_scan(table_name):

    ret_arr = []

    client = boto3.client('dynamodb')
    paginator = client.get_paginator('scan')
    operation_parameters = {
        'TableName': table_name
    }
    page_iterator = paginator.paginate(**operation_parameters)

    for page in page_iterator:
        for game in page['Items']:
            g = json.loads(game)
            ret_arr.append(g)

    return handle_response(func_name='dynamo_scan_table(3)',response=ret_arr)

