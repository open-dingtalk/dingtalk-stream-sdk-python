# !/usr/bin/env python

import sys

sys.path.append("../../")
sys.path.append("../")
sys.path.append(".")

import argparse
import logging
from dingtalk_stream import AckMessage
import dingtalk_stream
import time


def setup_logger():
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('%(asctime)s %(name)-8s %(levelname)-8s %(message)s [%(filename)s:%(lineno)d]'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


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


class CardBotHandler(dingtalk_stream.AsyncChatbotHandler):
    """
    接收回调消息。
    回复一个卡片，然后更新卡片的文本和图片。
    """

    def __init__(self, logger: logging.Logger = None, max_workers: int = 8):
        super(CardBotHandler, self).__init__(max_workers=max_workers)
        if logger:
            self.logger = logger

    def process(self, callback: dingtalk_stream.CallbackMessage):
        incoming_message = dingtalk_stream.ChatbotMessage.from_dict(callback.data)

        card_instance = self.reply_markdown_card("**这是一个markdown消息，初始状态，将于5s后更新**", incoming_message,
                                                 title="钉钉AI卡片",
                                                 logo="@lALPDfJ6V_FPDmvNAfTNAfQ")

        # 如果需要更新卡片内容的话，使用这个：
        time.sleep(5)
        card_instance.update("**这是一个markdown消息，已更新**")

        return AckMessage.STATUS_OK, 'OK'


def main():
    logger = setup_logger()
    options = define_options()

    credential = dingtalk_stream.Credential(options.client_id, options.client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)

    card_bot_handler = CardBotHandler(logger)

    client.register_callback_handler(dingtalk_stream.chatbot.ChatbotMessage.TOPIC, card_bot_handler)

    card_bot_handler.set_off_duty_prompt("不好意思，我已下班，请稍后联系我！")

    client.start_forever()


if __name__ == '__main__':
    main()
