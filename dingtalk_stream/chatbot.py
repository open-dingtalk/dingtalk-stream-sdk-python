import json
import urllib
import requests
from .stream import CallbackHandler


class AtUser(object):
    def __init__(self):
        self.dingtalk_id = None
        self.staff_id = None
        self.extensions = {}

    @classmethod
    def from_dict(cls, d):
        user = AtUser()
        data = ''
        for name, value in d.items():
            if name == 'dingtalkId':
                user.dingtalk_id = value
            elif name == 'staffId':
                user.staff_id = value
            else:
                user.extensions[name] = value
        return user

    def to_dict(self):
        result = self.extensions.copy()
        if self.dingtalk_id is not None:
            result['dingtalkId'] = self.dingtalk_id
        if self.staff_id is not None:
            result['staffId'] = self.staff_id
        return result


class TextContent(object):
    content: str

    def __init__(self):
        self.content = None
        self.extensions = {}

    def __str__(self):
        return 'TextContent(content=%s)' % self.content

    @classmethod
    def from_dict(cls, d):
        content = TextContent()
        data = ''
        for name, value in d.items():
            if name == 'content':
                content.content = value
            else:
                content.extensions[name] = value
        return content

    def to_dict(self):
        result = self.extensions.copy()
        if self.content is not None:
            result['content'] = self.content
        return result


class ChatbotMessage(object):
    TOPIC = '/v1.0/im/bot/messages/get'
    text: TextContent

    def __init__(self):
        self.is_in_at_list = None
        self.session_webhook = None
        self.sender_nick = None
        self.robot_code = None
        self.session_webhook_expired_time = None
        self.message_id = None
        self.sender_id = None
        self.chatbot_user_id = None
        self.conversation_id = None
        self.is_admin = None
        self.create_at = None
        self.text = None
        self.conversation_type = None
        self.at_users = []
        self.chatbot_corp_id = None
        self.sender_corp_id = None
        self.conversation_title = None
        self.message_type = None
        self.sender_staff_id = None

        self.extensions = {}

    @classmethod
    def from_dict(cls, d):
        msg = ChatbotMessage()
        data = ''
        for name, value in d.items():
            if name == 'isInAtList':
                msg.is_in_at_list = value
            elif name == 'sessionWebhook':
                msg.session_webhook = value
            elif name == 'senderNick':
                msg.sender_nick = value
            elif name == 'robotCode':
                msg.robot_code = value
            elif name == 'sessionWebhookExpiredTime':
                msg.session_webhook_expired_time = int(value)
            elif name == 'msgId':
                msg.message_id = value
            elif name == 'senderId':
                msg.sender_id = value
            elif name == 'chatbotUserId':
                msg.chatbot_user_id = value
            elif name == 'conversationId':
                msg.conversation_id = value
            elif name == 'isAdmin':
                msg.is_admin = value
            elif name == 'createAt':
                msg.create_at = value
            elif name == 'text':
                msg.text = TextContent.from_dict(value)
            elif name == 'conversationType':
                msg.conversation_type = value
            elif name == 'atUsers':
                msg.at_users = [AtUser.from_dict(i) for i in value]
            elif name == 'chatbotCorpId':
                msg.chatbot_corp_id = value
            elif name == 'senderCorpId':
                msg.sender_corp_id = value
            elif name == 'conversationTitle':
                msg.conversation_title = value
            elif name == 'msgtype':
                msg.message_type = value
            elif name == 'senderStaffId':
                msg.sender_staff_id = value
            else:
                msg.extensions[name] = value
        return msg

    def to_dict(self):
        result = self.extensions.copy()
        if self.is_in_at_list is not None:
            result['isInAtList'] = self.is_in_at_list
        if self.session_webhook is not None:
            result['sessionWebhook'] = self.session_webhook
        if self.sender_nick is not None:
            result['senderNick'] = self.sender_nick
        if self.robot_code is not None:
            result['robotCode'] = self.robot_code
        if self.session_webhook_expired_time is not None:
            result['sessionWebhookExpiredTime'] = self.session_webhook_expired_time
        if self.message_id is not None:
            result['msgId'] = self.message_id
        if self.sender_id is not None:
            result['senderId'] = self.sender_id
        if self.chatbot_user_id is not None:
            result['chatbotUserId'] = self.chatbot_user_id
        if self.conversation_id is not None:
            result['conversationId'] = self.conversation_id
        if self.is_admin is not None:
            result['isAdmin'] = self.is_admin
        if self.create_at is not None:
            result['createAt'] = self.create_at
        if self.text is not None:
            result['text'] = self.text.to_dict()
        if self.conversation_type is not None:
            result['conversationType'] = self.conversation_type
        if self.at_users is not None:
            result['atUsers'] = [i.to_dict() for i in self.at_users]
        if self.chatbot_corp_id is not None:
            result['chatbotCorpId'] = self.chatbot_corp_id
        if self.sender_corp_id is not None:
            result['senderCorpId'] = self.sender_corp_id
        if self.conversation_title is not None:
            result['conversationTitle'] = self.conversation_title
        if self.message_type is not None:
            result['msgtype'] = self.message_type
        if self.sender_staff_id is not None:
            result['senderStaffId'] = self.sender_staff_id
        return result

    def __str__(self):
        return 'ChatbotMessage(message_type=%s, text=%s, sender_nick=%s, conversation_title=%s)' % (
            self.message_type,
            self.text,
            self.sender_nick,
            self.conversation_title,
        )


class ChatbotHandler(CallbackHandler):
    def reply_text(self,
                         text: str,
                         incoming_message: ChatbotMessage):
        request_headers = {
            'Content-Type': 'application/json',
            'Accept': '*/*',
        }
        values = {
            'msgtype': 'text',
            'text': {
                'content': text,
            },
            'at': {
                'atUserIds': [incoming_message.sender_staff_id],
            }
        }
        try:
            response = requests.post(incoming_message.session_webhook,
                                     headers=request_headers,
                                     data=json.dumps(values))
            response.raise_for_status()
        except Exception as e:
            self.logger.error('reply text failed, error=%s', e)
            return None
        return response.json()

    def reply_markdown(self,
                       title: str,
                       text: str,
                       incoming_message: ChatbotMessage):
        request_headers = {
            'Content-Type': 'application/json',
            'Accept': '*/*',
        }
        values = {
            'msgtype': 'markdown',
            'markdown': {
                'title': title,
                'text': text,
            },
            'at': {
                'atUserIds': [incoming_message.sender_staff_id],
            }
        }
        try:
            response = requests.post(incoming_message.session_webhook,
                                     headers=request_headers,
                                     data=json.dumps(values))
            response.raise_for_status()
        except Exception as e:
            self.logger.error('reply markdown failed, error=%s', e)
            return None
        return response.json()
