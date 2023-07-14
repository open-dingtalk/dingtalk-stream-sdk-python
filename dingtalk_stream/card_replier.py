# -*- coding:utf-8 -*-
import uuid

import platform, requests, copy, hashlib
from .utils import DINGTALK_OPENAPI_ENDPOINT
from .log import setup_default_logger
from enum import Enum, unique


class CardReplier(object):

    def __init__(self, dingtalk_client, incoming_message):
        self.dingtalk_client = dingtalk_client
        self.incoming_message = incoming_message
        self.conversation_type = incoming_message.conversation_type
        self.open_conversation_id = incoming_message
        self.logger = setup_default_logger('dingtalk_stream.handler')

    @staticmethod
    def gen_card_id(msg):
        factor = '%s_%s_%s_%s_%s' % (
            msg.sender_id, msg.sender_corp_id, msg.conversation_id, msg.message_id, str(uuid.uuid1()))
        m = hashlib.sha256()
        m.update(factor.encode('utf-8'))
        return m.hexdigest()

    @staticmethod
    def get_request_header(access_token):
        return {
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'x-acs-dingtalk-access-token': access_token,
            'User-Agent': ('DingTalkStream/1.0 SDK/0.1.0 Python/%s '
                           '(+https://github.com/open-dingtalk/dingtalk-stream-sdk-python)'
                           ) % platform.python_version(),
        }

    def create_and_send_card(self, card_template_id: str, card_data: dict, callback_type: str = "",
                             callback_route_key: str = "", at_sender: bool = False,
                             at_all: bool = False) -> str:
        """
        发送卡片，两步骤：创建+投放。
        https://open.dingtalk.com/document/orgapp/interface-for-creating-a-card-instance
        :param card_template_id: 卡片模板ID
        :param card_data: 卡片数据
        :param at_sender:
        :param at_all:
        :return: 卡片的实例ID
        """
        access_token = self.dingtalk_client.get_access_token()
        if not access_token:
            self.logger.error(
                'CardResponder.send_card failed, cannot get dingtalk access token')
            return ""

        card_instance_id = self.gen_card_id(self.incoming_message)
        body = {
            # "userId": self.dingtalk_client.credential.client_id,
            "cardTemplateId": card_template_id,
            "outTrackId": card_instance_id,
            "cardData": {
                "cardParamMap": card_data
            },
            "imGroupOpenSpaceModel": {
                "supportForward": False
            },
            "imRobotOpenSpaceModel": {
                "supportForward": False
            }
        }

        if callback_type == "STREAM":
            body["callbackType"] = "STREAM"
        elif callback_type == "HTTP":
            body["callbackType"] = "HTTP"
            body["callbackRouteKey"] = callback_route_key

        # 创建卡片实例。https://open.dingtalk.com/document/orgapp/interface-for-creating-a-card-instance
        url = DINGTALK_OPENAPI_ENDPOINT + '/v1.0/card/instances'
        try:
            response = requests.post(url,
                                     headers=self.get_request_header(access_token),
                                     json=body)

            response.raise_for_status()
        except Exception as e:
            self.logger.error('CardResponder.send_card failed, create card instance failed, error=%s', e)
            return ""

        body = {
            "outTrackId": card_instance_id,
            "userIdType": 1
        }

        # 2：群聊，2：单聊
        if self.incoming_message.conversation_type == '2':
            body["openSpaceId"] = "dtv1.card//{spaceType}.{spaceId}".format(spaceType="IM_GROUP",
                                                                            spaceId=self.incoming_message.conversation_id)
            body["imGroupOpenDeliverModel"] = {
                "robotCode": self.dingtalk_client.credential.client_id,
            }

            if at_all:
                body["imGroupOpenDeliverModel"]["atUserIds"] = {
                    "@ALL": "@ALL",
                }
            elif at_sender:
                body["imGroupOpenDeliverModel"]["atUserIds"] = {
                    self.incoming_message.sender_staff_id: self.incoming_message.sender_nick,
                }

        elif self.incoming_message.conversation_type == '1':
            body["openSpaceId"] = "dtv1.card//{spaceType}.{spaceId}".format(spaceType="IM_ROBOT",
                                                                            spaceId=self.incoming_message.sender_staff_id)
            body["imRobotOpenDeliverModel"] = {
                "spaceType": "IM_ROBOT"
            }

        # 投放卡片。https://open.dingtalk.com/document/orgapp/delivery-card-interface
        url = DINGTALK_OPENAPI_ENDPOINT + '/v1.0/card/instances/deliver'
        try:
            response = requests.post(url,
                                     headers=self.get_request_header(access_token),
                                     json=body)

            response.raise_for_status()

            return card_instance_id
        except Exception as e:
            self.logger.error('put_card_data.create_and_send_card failed, send card failed, error=%s', e)
            return ""

    def put_card_data(self, card_instance_id: str, card_data: dict):
        """
        更新卡片内容
        https://open.dingtalk.com/document/orgapp/interactive-card-update-interface
        :param card_instance_id:
        :param card_data:
        :return:
        """
        access_token = self.dingtalk_client.get_access_token()
        if not access_token:
            self.logger.error(
                'CardReplier.put_card_data failed, cannot get dingtalk access token')
            return

        body = {
            "outTrackId": card_instance_id,
            "cardData": {
                "cardParamMap": card_data
            }
        }

        url = DINGTALK_OPENAPI_ENDPOINT + '/v1.0/card/instances'
        try:
            response = requests.put(url,
                                    headers=self.get_request_header(access_token),
                                    json=body)

            response.raise_for_status()
        except Exception as e:
            self.logger.error('CardReplier.put_card_data failed, update card failed, error=%s', e)
            return


@unique
class AICardStatus(str, Enum):
    PROCESSING: str = 1  # 处理中
    INPUTING: str = 2  # 输入中
    EXECUTING: str = 4  # 执行中
    FINISHED: str = 3  # 执行完成
    FAILED: str = 5  # 执行失败


class AICardReplier(CardReplier):

    def __init__(self, dingtalk_client, incoming_message):
        super(AICardReplier, self).__init__(dingtalk_client, incoming_message)

    def start(self, card_template_id: str, card_data: dict) -> str:
        """
        AI卡片的创建接口
        :param card_template_id:
        :param card_data:
        :return:
        """
        card_data_with_status = copy.deepcopy(card_data)
        card_data_with_status["flowStatus"] = AICardStatus.PROCESSING
        return self.create_and_send_card(card_template_id, card_data_with_status, at_sender=False, at_all=False)

    def finish(self, card_instance_id: str, card_data: dict):
        """
        AI卡片执行完成的接口，整体更新
        :param card_instance_id:
        :param card_data:
        :return:
        """
        card_data_with_status = copy.deepcopy(card_data)
        card_data_with_status["flowStatus"] = AICardStatus.FINISHED
        self.put_card_data(card_instance_id, card_data_with_status)

    def fail(self, card_instance_id: str, card_data: dict):
        """
        AI卡片变成失败状态的接口，整体更新，非streaming
        :param card_instance_id:
        :param card_data:
        :return:
        """
        card_data_with_status = copy.deepcopy(card_data)
        card_data_with_status["flowStatus"] = AICardStatus.FAILED
        self.put_card_data(card_instance_id, card_data_with_status)

    def streaming(self, card_instance_id: str, content_key: str, content_value: str, append: bool, finished: bool,
                  failed: bool):
        """
        AI卡片的流式输出
        :param card_instance_id:
        :param content_key:
        :param content_value:
        :param append:
        :param finished:
        :param failed:
        :return:
        """
        access_token = self.dingtalk_client.get_access_token()
        if not access_token:
            self.logger.error(
                'AICardReplier.streaming failed, cannot get dingtalk access token')
            return None

        body = {
            "outTrackId": card_instance_id,
            "guid": str(uuid.uuid1()),
            "key": content_key,
            "content": content_value,
            "isFull": not append,
            "isFinalize": finished,
            "isError": failed,
        }

        url = DINGTALK_OPENAPI_ENDPOINT + '/v1.0/card/streaming'
        try:
            response = requests.put(url,
                                    headers=self.get_request_header(access_token),
                                    json=body)

            response.raise_for_status()
        except Exception as e:
            self.logger.error('AICardReplier.streaming failed, error=%s', e)
            return
