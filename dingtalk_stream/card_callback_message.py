# -*- coding:utf-8 -*-

import json

Card_Callback_Router_Topic = '/v1.0/card/instances/callback'


class CardCallbackMessage(object):

    def __init__(self):
        self.extension = {}
        self.corp_id = ""
        self.space_type = ""
        self.user_id_type = -1
        self.type = "actionCallback"
        self.user_id = ""
        self.content = {}
        self.space_id = ""
        self.card_instance_id = ""
        self.value = {}

    {"extension": "{}", "corpId": "ding9f50b15bccd16741", "spaceType": "", "userIdType": 1, "type": "actionCallback",
     "userId": "04574258341072934",
     "content": "{\"cardPrivateData\":{\"actionIds\":[\"button_node_ocljnpbz4i4\"],\"params\":{}}}", "spaceId": "",
     "outTrackId": "53d6dda444c74f5f17bf4534333c1a46f690b4ddadac8d7e80fc11c2e4a714cb",
     "value": "{\"cardPrivateData\":{\"actionIds\":[\"button_node_ocljnpbz4i4\"],\"params\":{}}}"}


    @classmethod
    def from_dict(cls, d):
        msg = CardCallbackMessage()
        for name, value in d.items():
            if name == 'extension':
                msg.extension = json.loads(value)
            elif name == 'corpId':
                msg.corp_id = value
            elif name == "userId":
                msg.user_id = value
            elif name == 'outTrackId':
                msg.card_instance_id = value
            elif name == "value":
                msg.value = json.loads(value)
        return msg

