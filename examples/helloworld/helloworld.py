#!/usr/bin/env python

import argparse
from dingtalk_stream import AckMessage
import dingtalk_stream


def define_options():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--client_id', dest='client_id', required=True,
        help='app_key or suite_key from https://open-dev.digntalk.com'
    )
    parser.add_argument(
        '--client_secret', dest='client_secret', required=True,
        help='app_secret or suite_secret from https://open-dev.digntalk.com'
    )
    options = parser.parse_args()
    return options


class MyEventHandler(dingtalk_stream.EventHandler):
    async def process(self, event: dingtalk_stream.EventMessage):
        print(event.headers.event_type,
              event.headers.event_id,
              event.headers.event_born_time,
              event.data)
        return AckMessage.STATUS_OK, 'OK'


class MyCallbackHandler(dingtalk_stream.CallbackHandler):
    async def process(self, message: dingtalk_stream.CallbackMessage):
        print(message.headers.topic,
              message.data)
        return AckMessage.STATUS_OK, 'OK'


def main():
    options = define_options()

    credential = dingtalk_stream.Credential(options.client_id, options.client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_all_event_handler(MyEventHandler())
    client.register_callback_handler(dingtalk_stream.ChatbotMessage.TOPIC, MyCallbackHandler())
    client.start_forever()


if __name__ == '__main__':
    main()
