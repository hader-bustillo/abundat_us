import boto3
import logging
import json

logger = logging.getLogger(__name__)


def get_message_from_sqs(sqs_queue):

    # get the sqs
    sqs_client = boto3.client('sqs', region_name="us-east-2")

    # get the queue object

    sqs_queue_url = get_queue_url(sqs_queue=sqs_queue)

    #proces the message in the queue

    response = sqs_client.receive_message(
        QueueUrl=sqs_queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10,
    )

    response_message = []

    try:
        response_message = response.get('Messages', [])
    except Exception as e:
        logging.exception("Error encountered in receiving the message from queue - %s", repr(sqs_queue))

    if response_message:
        delete_message(receipt_handle=response_message[0]['ReceiptHandle'],
                       queue_url=sqs_queue_url)
        response_message = json.loads(response_message[0]["Body"])
    return response_message


def delete_message(receipt_handle, queue_url):
    sqs_client = boto3.client("sqs", region_name="us-east-2")
    response = sqs_client.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle,
    )
    logging.info(repr(response))


def get_queue_url(sqs_queue):
    sqs_client = boto3.client("sqs", region_name="us-east-2")
    response = sqs_client.get_queue_url(
        QueueName=sqs_queue,
    )
    return response["QueueUrl"]


def put_message_to_sqs(sqs_queue, message):
    sqs = boto3.client('sqs', region_name="us-east-2")

    sqs_queue_url = get_queue_url(sqs_queue=sqs_queue)

    logging.info("Received request to put message %s on to queue - %s", repr(message), repr(sqs_queue))
    queue = sqs.get_queue_by_name(QueueName=sqs_queue)

    try:
        response = sqs.send_message(
            QueueUrl=sqs_queue_url,
            MessageBody=json.dumps(message)
        )

        logging.info("received response %s on putting the message %s to the queue", repr(response), repr(sqs_queue))
    except Exception as e:
        logging.exception("Error in putting message %s to the queue %s", repr(message), repr(sqs_queue))
