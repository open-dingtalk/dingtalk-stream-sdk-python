#!/usr/bin/env python3

import asyncio
import asyncio.exceptions
import json
import logging
import platform
import time
import requests
import socket
import websockets

from urllib.parse import quote_plus

from .credential import Credential
from .handlers import CallbackHandler
from .handlers import EventHandler
from .handlers import SystemHandler
from .frames import SystemMessage
from .frames import EventMessage
from .frames import CallbackMessage
from .log import setup_default_logger
from .utils import DINGTALK_OPENAPI_ENDPOINT
from .version import VERSION_STRING


class DingTalkStreamClient(object):
    OPEN_CONNECTION_API = DINGTALK_OPENAPI_ENDPOINT + '/v1.0/gateway/connections/open'
    TAG_DISCONNECT = 'disconnect'
    HTTP_TIMEOUT_SECONDS = 10
    MAX_PENDING_TASKS = 100

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
        self._runner_task = None
        self._stop_event = None
        self._connection_tasks = set()

    def register_all_event_handler(self, handler: EventHandler):
        handler.dingtalk_client = self
        self.event_handler = handler
        self._is_event_required = True

    def register_callback_handler(self, topic, handler: CallbackHandler):
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
        current_task = asyncio.current_task()
        if self._runner_task is not None and not self._runner_task.done():
            raise RuntimeError('DingTalk stream client is already running')

        self._runner_task = current_task
        self._stop_event = asyncio.Event()
        try:
            while not self._stop_event.is_set():
                try:
                    loop = asyncio.get_running_loop()
                    connection = await loop.run_in_executor(None, self.open_connection)

                    if self._stop_event.is_set():
                        break
                    if not connection:
                        self.logger.error('open connection failed')
                        await self._wait_before_retry(10)
                        continue
                    self.logger.info('connecting to endpoint %s', connection['endpoint'])

                    uri = f'{connection["endpoint"]}?ticket={quote_plus(connection["ticket"])}'
                    async with websockets.connect(uri) as websocket:
                        self.websocket = websocket
                        keepalive_task = asyncio.create_task(self.keepalive(websocket))
                        try:
                            async for raw_message in websocket:
                                try:
                                    json_message = json.loads(raw_message)
                                except (TypeError, json.JSONDecodeError):
                                    self.logger.warning('invalid message, content=%r', raw_message)
                                    continue
                                if len(self._connection_tasks) >= self.MAX_PENDING_TASKS:
                                    await asyncio.wait(
                                        self._connection_tasks,
                                        return_when=asyncio.FIRST_COMPLETED,
                                    )
                                task = asyncio.create_task(self.background_task(json_message, websocket))
                                self._connection_tasks.add(task)
                                task.add_done_callback(self._connection_tasks.discard)
                        finally:
                            keepalive_task.cancel()
                            await asyncio.gather(keepalive_task, return_exceptions=True)
                            await self._cancel_connection_tasks()
                            if self.websocket is websocket:
                                self.websocket = None
                except asyncio.exceptions.CancelledError:
                    raise
                except websockets.exceptions.ConnectionClosedError as e:
                    self.logger.error('[start] network exception, error=%s', e)
                    await self._wait_before_retry(10)
                except Exception:
                    self.logger.exception('unknown exception')
                    await self._wait_before_retry(3)
        finally:
            await self._cancel_connection_tasks()
            websocket = self.websocket
            self.websocket = None
            if websocket is not None:
                await websocket.close()
            self._runner_task = None
            self._stop_event = None

    async def stop(self):
        """Stop reconnecting and close the currently active websocket."""
        if self._stop_event is not None:
            self._stop_event.set()
        websocket = self.websocket
        if websocket is not None:
            await websocket.close()

    async def _wait_before_retry(self, delay):
        if self._stop_event is None or self._stop_event.is_set():
            return
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass

    async def _cancel_connection_tasks(self):
        tasks = list(self._connection_tasks)
        self._connection_tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def keepalive(self, ws, ping_interval=60):
        while True:
            await asyncio.sleep(ping_interval)
            try:
                await ws.ping()
            except websockets.exceptions.ConnectionClosed:
                break

    async def background_task(self, json_message, websocket=None):
        target_websocket = websocket if websocket is not None else self.websocket
        try:
            route_result = await self.route_message(json_message, target_websocket)
            if route_result == DingTalkStreamClient.TAG_DISCONNECT and target_websocket is not None:
                await target_websocket.close()
        except asyncio.exceptions.CancelledError:
            raise
        except Exception:
            self.logger.exception('error processing message')

    async def route_message(self, json_message, websocket=None):
        target_websocket = websocket if websocket is not None else self.websocket
        result = ''
        msg_type = json_message.get('type', '')
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
        if ack and target_websocket is not None:
            await target_websocket.send(json.dumps(ack.to_dict()))
        return result

    def start_forever(self):
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            pass

    def open_connection(self):
        self.logger.info('open connection, url=%s' % DingTalkStreamClient.OPEN_CONNECTION_API)
        request_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': ('DingTalkStream/1.0 SDK/%s Python/%s '
                           '(+https://github.com/open-dingtalk/dingtalk-stream-sdk-python)'
                           ) % (VERSION_STRING, platform.python_version()),
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
            'ua': 'dingtalk-sdk-python/v%s-union' % VERSION_STRING,
            'localIp': self.get_host_ip()
        }).encode('utf-8')

        try:
            response_text = ''
            response = requests.post(DingTalkStreamClient.OPEN_CONNECTION_API,
                                     headers=request_headers,
                                     data=request_body,
                                     timeout=self.HTTP_TIMEOUT_SECONDS)
            response_text = response.text
            
            response.raise_for_status()
        except Exception as e:
            self.logger.error(f'open connection failed, error={e}, response.text={response_text}')
            return None
        return response.json()

    def get_host_ip(self):
        """
        查询本机ip地址
        :return: ip
        """
        ip = ''
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(('8.8.8.8', 80))
                return sock.getsockname()[0]
        except OSError:
            return ip

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
            url = DINGTALK_OPENAPI_ENDPOINT + '/v1.0/oauth2/accessToken'
            response_text = ''
            response = requests.post(url,
                                     headers=request_headers,
                                     data=json.dumps(values),
                                     timeout=self.HTTP_TIMEOUT_SECONDS)
            response_text = response.text
            
            response.raise_for_status()
        except Exception as e:
            self.logger.error(f'get dingtalk access token failed, error={e}, response.text={response_text}')
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
        upload_url = f'https://oapi.dingtalk.com/media/upload?access_token={quote_plus(access_token)}'
        try:
            response_text = ''
            response = requests.post(upload_url,
                                     data=values,
                                     files=files,
                                     timeout=self.HTTP_TIMEOUT_SECONDS)
            response_text = response.text
            if response.status_code == 401:
                self.reset_access_token()

            response.raise_for_status()
        except Exception as e:
            self.logger.error(f'upload to dingtalk failed, error={e}, response.text={response_text}')
            return None
        if 'media_id' not in response.json():
            self.logger.error('upload to dingtalk failed, error response is %s', response.json())
            raise Exception('upload failed, error=%s' % response.json())
        return response.json()['media_id']
