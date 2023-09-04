# !/usr/bin/env python

import argparse
import logging
from dingtalk_stream import AckMessage
import dingtalk_stream

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


class CardCallbackHandler(dingtalk_stream.CallbackHandler):
    def __init__(self, logger: logging.Logger = None):
        super(dingtalk_stream.CallbackHandler, self).__init__()
        if logger:
            self.logger = logger

    async def process(self, callback: dingtalk_stream.CallbackMessage):
        # 卡片回调的数据构造详见文档：https://open.dingtalk.com/document/orgapp/instructions-for-filling-in-api-card-data
        response = {
            'cardData': {
                'cardParamMap': {
                    'intParam': '1',
                    'trueParam': 'true',
                }},
            'privateData': {
                'myUserId': {
                    'cardParamMap': {
                        'floatParam': '1.23',
                        'falseparam': 'false',
                    },
                }
            }
        }
        return AckMessage.STATUS_OK, response


def main():
    logger = setup_logger()
    options = define_options()

    credential = dingtalk_stream.Credential(options.client_id, options.client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_callback_handler(dingtalk_stream.CallbackHandler.TOPIC_CARD_CALLBACK,
                                     CardCallbackHandler(logger))
    client.start_forever()


if __name__ == '__main__':
    main()
