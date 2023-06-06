# !/usr/bin/env python

import sys

sys.path.append("../../")
sys.path.append("../")
sys.path.append(".")

import argparse
import logging
from dingtalk_stream import AckMessage, interactive_card
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


class CardBotHandler(dingtalk_stream.ChatbotHandler):
    """
    接收回调消息。
    回复一个卡片，然后更新卡片的文本和图片。
    """

    def __init__(self, logger: logging.Logger = None):
        super(dingtalk_stream.ChatbotHandler, self).__init__()
        if logger:
            self.logger = logger

    async def process(self, callback: dingtalk_stream.CallbackMessage):
        incoming_message = dingtalk_stream.ChatbotMessage.from_dict(callback.data)

        # 先回复一个卡片
        self.reply_card(interactive_card.INTERACTIVE_CARD_JSON_SAMPLE_1,
                        incoming_message, False)

        time.sleep(1)

        card_data = interactive_card.INTERACTIVE_CARD_JSON_SAMPLE_1.copy()

        # 更新文本
        card_data["contents"][0]["text"] = "钉钉，让进步发生！\n 更新时间：{tt}".format(
            tt=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

        # 上传图片
        media_id = self.dingtalk_client.upload_to_dingtalk(open('./img.png', 'rb'),
                                                           filetype='image',
                                                           filename='image.png',
                                                           mimetype='image/png')
        # 更新图片
        card_data["contents"][1]["image"] = media_id

        # 更新卡片
        self.update_card(card_data,
                         incoming_message)

        return AckMessage.STATUS_OK, 'OK'


def main():
    logger = setup_logger()
    options = define_options()

    credential = dingtalk_stream.Credential(options.client_id, options.client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_callback_hanlder(dingtalk_stream.chatbot.ChatbotMessage.TOPIC, CardBotHandler(logger))
    client.start_forever()


if __name__ == '__main__':
    main()
