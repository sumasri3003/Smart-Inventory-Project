import os
import json
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from dotenv import load_dotenv

load_dotenv()

CONN_STR = os.getenv("SERVICE_BUS_CONNECTION_STRING")
QUEUE_NAME = os.getenv("SERVICE_BUS_QUEUE_NAME")


def publish_order_event(order_event: dict):
    if not CONN_STR or not QUEUE_NAME:
        raise ValueError("Service Bus connection details are missing in .env")

    message_body = json.dumps(order_event)

    with ServiceBusClient.from_connection_string(CONN_STR) as client:
        sender = client.get_queue_sender(queue_name=QUEUE_NAME)
        with sender:
            message = ServiceBusMessage(message_body)
            sender.send_messages(message)

    print(f" Order event sent to Service Bus queue: {QUEUE_NAME}")
