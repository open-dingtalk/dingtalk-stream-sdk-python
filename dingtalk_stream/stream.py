#!/usr/bin/env python3

import asyncio
import asyncio.exceptions
import json
import logging
import platform
import time
import urllib.error
import urllib.parse
import urllib.request
import requests

import websockets

from .credential import Credential
from .handlers import CallbackHandler
from .handlers import EventHandler
from .handlers import SystemHandler
from .frames import SystemMessage
from .frames import EventMessage
from .frames import CallbackMessage
from .log import setup_default_logger
from .utils import DINGTALK_OPENAPI_ENDPOINT


class DingTalkStreamClient(object):
    OPEN_CONNECTION_API = DINGTALK_OPENAPI_ENDPOINT + '/v1.0/gateway/connections/open'
    TAG_DISCONNECT = 'disconnect'

    def __init__(self, credential: Credential, logger: logging.Logger = None):
        self.credential: Credential = credential
        self.event_handler: EventHandler = EventHandler()
        self.callback_handler_map = {}
        self.system_handler: SystemHandler = SystemHandler()
        self.websocket = None  # create websocket client after connected
        self.logger: logging.Logger = logger if logger else setup_default_logger('dingtalk_stream.client')
        self._pre_started = False
        self._is_event_required = False
        self._access_token = {}

    def register_all_event_handler(self, handler: EventHandler):
        handler.dingtalk_client = self
        self.event_handler = handler
        self._is_event_required = True

    def register_callback_hanlder(self, topic, handler: CallbackHandler):
        handler.dingtalk_client = self
        self.callback_handler_map[topic] = handler

    def pre_start(self):
        if self._pre_started:
            return
        self._pre_started = True
        self.event_handler.pre_start()
        self.system_handler.pre_start()
        for handler in self.callback_handler_map.values():
            handler.pre_start()

    async def start(self):
        self.pre_start()

        while True:
            connection = self.open_connection()

            if not connection:
                self.logger.error('open connection failed')
                time.sleep(10)
                continue
            self.logger.info('endpoint is %s', connection)

            uri = '%s?ticket=%s' % (connection['endpoint'], urllib.parse.quote_plus(connection['ticket']))
            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
                async for raw_message in websocket:
                    json_message = json.loads(raw_message)
                    route_result = await self.route_message(json_message)
                    if route_result == DingTalkStreamClient.TAG_DISCONNECT:
                        break
                # self.websocket.close()
        return

    async def route_message(self, json_message):
        result = ''
        msg_type = json_message.get('type', '')
        headers = json_message.get('headers', {})
        topic = headers.get('topic', '')
        ack = None
        if msg_type == SystemMessage.TYPE:
            msg = SystemMessage.from_dict(json_message)
            ack = await self.system_handler.raw_process(msg)
            if msg.headers.topic == SystemMessage.TOPIC_DISCONNECT:
                result = DingTalkStreamClient.TAG_DISCONNECT
                self.logger.info("received disconnect topic=%s, message=%s", msg.headers.topic, json_message)
            else:
                self.logger.warning("unknown message topic, topic=%s, message=%s", msg.headers.topic, json_message)
        elif msg_type == EventMessage.TYPE:
            msg = EventMessage.from_dict(json_message)
            ack = await self.event_handler.raw_process(msg)
        elif msg_type == CallbackMessage.TYPE:
            msg = CallbackMessage.from_dict(json_message)
            handler = self.callback_handler_map.get(msg.headers.topic)
            if handler:
                ack = await handler.raw_process(msg)
            else:
                self.logger.warning("unknown callback message topic, topic=%s, message=%s", msg.headers.topic,
                                    json_message)
        else:
            self.logger.warning('unknown message, content=%s', json_message)
        if ack:
            await self.websocket.send(json.dumps(ack.to_dict()))
        return result

    def start_forever(self):
        while True:
            try:
                asyncio.run(self.start())
            except (asyncio.exceptions.CancelledError,
                    websockets.exceptions.ConnectionClosedError) as e:
                self.logger.error('network exception, error=%s', e)
                time.sleep(10)
                continue
            except Exception as e:
                time.sleep(3)
                self.logger.exception('unknown exception', e)
            finally:
                continue

    def open_connection(self):
        self.logger.info('open connection, url=%s' % DingTalkStreamClient.OPEN_CONNECTION_API)
        request_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': ('DingTalkStream/1.0 SDK/0.1.0 Python/%s '
                           '(+https://github.com/open-dingtalk/dingtalk-stream-sdk-python)'
                           ) % platform.python_version(),
        }
        topics = []
        if self._is_event_required:
            topics.append({'type': 'EVENT', 'topic': '*'})
        for topic in self.callback_handler_map.keys():
            topics.append({'type': 'CALLBACK', 'topic': topic})
        request_body = json.dumps({
            'clientId': self.credential.client_id,
            'clientSecret': self.credential.client_secret,
            'subscriptions': topics,
        }).encode('utf-8')

        try:
            response = requests.post(DingTalkStreamClient.OPEN_CONNECTION_API,
                                     headers=request_headers,
                                     data=request_body)
            http_body = response.json()
            response.raise_for_status()
        except Exception as e:
            self.logger.error("open connection failed, error=%s, response.body=%s", e, http_body)
            return None
        return response.json()

    def reset_access_token(self):
        """ reset token if open api return 401 """
        self._access_token = {}

    def get_access_token(self):
        now = int(time.time())
        if self._access_token and now < self._access_token['expireTime']:
            return self._access_token['accessToken']

        request_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        values = {
            'appKey': self.credential.client_id,
            'appSecret': self.credential.client_secret,
        }
        try:
            response = requests.post(DINGTALK_OPENAPI_ENDPOINT + '/v1.0/oauth2/accessToken',
                                     headers=request_headers,
                                     data=json.dumps(values))
            response.raise_for_status()
        except Exception as e:
            self.logger.error('get dingtalk access token failed, error=%s', e)
            return None

        result = response.json()
        result['expireTime'] = int(time.time()) + result['expireIn'] - (5 * 60)  # reserve 5min buffer time
        self._access_token = result
        return self._access_token['accessToken']

    def upload_to_dingtalk(self, image_content, filetype='image', filename='image.png', mimetype='image/png'):
        access_token = self.get_access_token()
        if not access_token:
            self.logger.error('upload_to_dingtalk failed, cannot get dingtalk access token')
            return None
        files = {
            'media': (filename, image_content, mimetype),
        }
        values = {
            'type': filetype,
        }
        upload_url = ('https://oapi.dingtalk.com/media/upload?access_token=%s'
                      ) % urllib.parse.quote_plus(access_token)
        try:
            response = requests.post(upload_url, data=values, files=files)
            if response.status_code == 401:
                self.reset_access_token()
            response.raise_for_status()
        except Exception as e:
            self.logger.error('upload to dingtalk failed, error=%s', e)
            return None
        return response.json()['media_id']
