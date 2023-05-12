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


class CalcBotHandler(dingtalk_stream.ChatbotHandler):
    async def process(self, callback: dingtalk_stream.CallbackMessage):
        incoming_message = dingtalk_stream.ChatbotMessage.from_dict(callback.data)
        expression = incoming_message.text.content.strip()
        try:
            result = eval(expression)
        except Exception as e:
            result = 'Error: %s' % e
        print('%s = %s' % (expression, result))
        response = 'Q: %s\nA: %s' % (expression, result)
        await self.reply_text(response, incoming_message)
        return AckMessage.STATUS_OK, 'OK'


def main():
    options = define_options()

    credential = dingtalk_stream.Credential(options.client_id, options.client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_callback_hanlder(dingtalk_stream.ChatbotMessage.TOPIC, CalcBotHandler())
    client.start_forever()


if __name__ == '__main__':
    main()
