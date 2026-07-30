import asyncio
import json
import unittest
from unittest import mock

from dingtalk_stream.credential import Credential
from dingtalk_stream.frames import AckMessage
from dingtalk_stream.stream import DingTalkStreamClient


class FakeWebSocket:

    def __init__(self):
        self.closed = False
        self.sent = []

    async def close(self):
        self.closed = True

    async def send(self, data):
        self.sent.append(data)


class DingTalkStreamClientTest(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.client = DingTalkStreamClient(Credential('client-id', 'client-secret'))

    async def test_start_propagates_cancellation(self):
        self.client.open_connection = mock.Mock(return_value=None)
        task = asyncio.create_task(self.client.start())
        await asyncio.sleep(0)
        task.cancel()

        with self.assertRaises(asyncio.CancelledError):
            await task

        self.assertIsNone(self.client._runner_task)

    async def test_stop_interrupts_retry_delay(self):
        self.client.open_connection = mock.Mock(return_value=None)
        task = asyncio.create_task(self.client.start())
        while self.client._stop_event is None:
            await asyncio.sleep(0)

        await self.client.stop()
        await asyncio.wait_for(task, timeout=1)

        self.assertIsNone(self.client._runner_task)

    async def test_ack_is_sent_to_source_websocket(self):
        old_websocket = FakeWebSocket()
        new_websocket = FakeWebSocket()
        self.client.websocket = new_websocket
        ack = AckMessage()
        ack.code = 200
        ack.message = 'OK'
        self.client.event_handler.raw_process = mock.AsyncMock(return_value=ack)
        message = {
            'type': 'EVENT',
            'headers': {'topic': 'test-topic', 'messageId': 'message-id'},
            'data': '{}',
        }

        await self.client.route_message(message, old_websocket)

        self.assertEqual(1, len(old_websocket.sent))
        self.assertEqual(200, json.loads(old_websocket.sent[0])['code'])
        self.assertEqual([], new_websocket.sent)

    def test_open_connection_has_timeout(self):
        response = mock.Mock()
        response.text = '{}'
        response.json.return_value = {}
        with mock.patch('dingtalk_stream.stream.requests.post', return_value=response) as post:
            self.client.open_connection()

        self.assertEqual(
            DingTalkStreamClient.HTTP_TIMEOUT_SECONDS,
            post.call_args.kwargs['timeout'],
        )


if __name__ == '__main__':
    unittest.main()
