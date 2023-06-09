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
import copy, asyncio


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
        '''
        多线程场景，process函数不要用 async 修饰
        :param message:
        :return:
        '''

        incoming_message = dingtalk_stream.ChatbotMessage.from_dict(callback.data)

        texts = [
            "第一行文本"
        ]

        # 先回复一个文本卡片
        self.reply_card(
            interactive_card.generate_multi_text_line_card_data(title="机器人名字", logo="@lALPDfJ6V_FPDmvNAfTNAfQ",
                                                                texts=texts),
            incoming_message, False)

        images = [
            "@lADPDe7s2ySi18PNA6XNBXg",
            "@lADPDf0i1beuNF3NAxTNBXg",
            "@lADPDe7s2ySRnIvNA6fNBXg"
        ]

        # 再回复一个文本+图片卡片
        card_biz_id = self.reply_card(
            interactive_card.generate_multi_text_image_card_data(title="机器人名字", logo="@lALPDfJ6V_FPDmvNAfTNAfQ",
                                                                 texts=texts, images=images),
            incoming_message, False)

        # 再试试更新卡片
        time.sleep(3)

        # 上传图片
        media_id = self.dingtalk_client.upload_to_dingtalk(open('./img.png', 'rb'),
                                                           filetype='image',
                                                           filename='image.png',
                                                           mimetype='image/png')

        texts = [
            "更新后的第一行文本",
            "更新后的第二行文本"
        ]

        self.update_card(card_biz_id, interactive_card.generate_multi_text_image_card_data(title="机器人名字",
                                                                                           logo="@lALPDfJ6V_FPDmvNAfTNAfQ",
                                                                                           texts=texts,
                                                                                           images=[media_id]))

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
