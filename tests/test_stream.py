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


class EmptyWebSocket(FakeWebSocket):

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


class FakeWebSocketConnect:

    def __init__(self, websocket):
        self.websocket = websocket

    async def __aenter__(self):
        return self.websocket

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


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

    def test_reconnect_delay_uses_bounded_exponential_backoff(self):
        with mock.patch(
                'dingtalk_stream.stream.random.uniform',
                return_value=0.5):
            self.assertEqual(1.5, self.client._reconnect_delay(0))
            self.assertEqual(2.5, self.client._reconnect_delay(1))
            self.assertEqual(4.5, self.client._reconnect_delay(2))
            self.assertEqual(
                self.client.RECONNECT_MAX_DELAY_SECONDS,
                self.client._reconnect_delay(100),
            )

    async def test_normal_websocket_close_uses_reconnect_backoff(self):
        options = {
            'open_timeout': 3,
            'ping_interval': None,
        }
        self.client = DingTalkStreamClient(
            Credential('client-id', 'client-secret'),
            websocket_connect_options=options,
        )
        options['open_timeout'] = 99
        self.client.open_connection = mock.Mock(return_value={
            'endpoint': 'ws://localhost',
            'ticket': 'test-ticket',
        })
        observed_delays = []

        async def stop_after_delay(delay):
            observed_delays.append(delay)
            self.client._stop_event.set()

        self.client._reconnect_delay = mock.Mock(return_value=1.25)
        self.client._wait_before_retry = stop_after_delay
        with mock.patch(
                'dingtalk_stream.stream.websockets.connect',
                return_value=FakeWebSocketConnect(EmptyWebSocket())) as connect:
            await self.client.start()

        self.assertEqual([1.25], observed_delays)
        self.client._reconnect_delay.assert_called_once_with(0)
        self.assertEqual(1, self.client.open_connection.call_count)
        connect.assert_called_once_with(
            'ws://localhost?ticket=test-ticket',
            open_timeout=3,
            ping_interval=None,
        )

    async def test_stop_interrupts_wait_for_background_task_capacity(self):
        self.client._stop_event = asyncio.Event()
        blocker = asyncio.Event()
        tasks = {
            asyncio.create_task(blocker.wait())
            for _ in range(self.client.MAX_PENDING_TASKS)
        }
        self.client._connection_tasks.update(tasks)
        capacity_waiter = asyncio.create_task(self.client._wait_for_task_capacity())
        await asyncio.sleep(0)

        await self.client.stop()

        self.assertFalse(await asyncio.wait_for(capacity_waiter, timeout=1))
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.client._connection_tasks.clear()

    async def test_task_ignoring_cancellation_remains_globally_bounded(self):
        self.client.TASK_CANCELLATION_TIMEOUT_SECONDS = 0.01
        cancellation_received = asyncio.Event()
        release_task = asyncio.Event()

        async def ignore_cancellation():
            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                cancellation_received.set()
                await release_task.wait()

        task = asyncio.create_task(ignore_cancellation())
        self.client._connection_tasks.add(task)
        await asyncio.sleep(0)

        await asyncio.wait_for(self.client._cancel_connection_tasks(), timeout=1)

        self.assertTrue(cancellation_received.is_set())
        self.assertNotIn(task, self.client._connection_tasks)
        self.assertIn(task, self.client._orphaned_tasks)

        self.client._stop_event = asyncio.Event()
        blockers = {
            asyncio.create_task(asyncio.sleep(3600))
            for _ in range(self.client.MAX_PENDING_TASKS - 1)
        }
        self.client._connection_tasks.update(blockers)
        capacity_waiter = asyncio.create_task(self.client._wait_for_task_capacity())
        await asyncio.sleep(0)
        self.assertFalse(capacity_waiter.done())

        release_task.set()
        await task
        await asyncio.wait_for(capacity_waiter, timeout=1)
        self.assertNotIn(task, self.client._orphaned_tasks)

        for blocker in blockers:
            blocker.cancel()
        await asyncio.gather(*blockers, return_exceptions=True)
        self.client._connection_tasks.clear()

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

    async def test_duplicate_message_shares_handler_and_replays_ack(self):
        first_websocket = FakeWebSocket()
        retry_websocket = FakeWebSocket()
        cached_retry_websocket = FakeWebSocket()
        handler_started = asyncio.Event()
        release_handler = asyncio.Event()
        handler_calls = 0

        async def process_once(_):
            nonlocal handler_calls
            handler_calls += 1
            handler_started.set()
            await release_handler.wait()
            ack = AckMessage()
            ack.code = 200
            ack.message = 'OK'
            return ack

        self.client.event_handler.raw_process = process_once
        message = {
            'type': 'EVENT',
            'headers': {'topic': 'test-topic', 'messageId': 'duplicate-message-id'},
            'data': '{}',
        }

        first = asyncio.create_task(self.client.background_task(message, first_websocket))
        await handler_started.wait()
        retry = asyncio.create_task(self.client.background_task(message, retry_websocket))
        await asyncio.sleep(0)
        release_handler.set()
        await asyncio.gather(first, retry)
        await self.client.background_task(message, cached_retry_websocket)

        self.assertEqual(1, handler_calls)
        self.assertEqual(1, len(first_websocket.sent))
        self.assertEqual(1, len(retry_websocket.sent))
        self.assertEqual(1, len(cached_retry_websocket.sent))
        self.assertEqual({}, self.client._inflight_messages)

    async def test_failed_message_result_is_not_cached(self):
        handler_calls = 0

        async def fail_for_retry(_):
            nonlocal handler_calls
            handler_calls += 1
            ack = AckMessage()
            ack.code = AckMessage.STATUS_SYSTEM_EXCEPTION
            ack.message = 'retry'
            return ack

        self.client.event_handler.raw_process = fail_for_retry
        message = {
            'type': 'EVENT',
            'headers': {'topic': 'test-topic', 'messageId': 'retry-message-id'},
            'data': '{}',
        }

        await self.client.background_task(message, FakeWebSocket())
        await self.client.background_task(message, FakeWebSocket())

        self.assertEqual(2, handler_calls)
        self.assertNotIn('retry-message-id', self.client._message_results)

    async def test_system_message_is_not_deduplicated_across_connections(self):
        ack = AckMessage()
        ack.code = AckMessage.STATUS_OK
        ack.message = 'OK'
        self.client.logger = mock.Mock()
        self.client.system_handler.raw_process = mock.AsyncMock(return_value=ack)
        message = {
            'type': 'SYSTEM',
            'headers': {'topic': 'ping', 'messageId': 'system-message-id'},
            'data': '{}',
        }

        await self.client.background_task(message, FakeWebSocket())
        await self.client.background_task(message, FakeWebSocket())

        self.assertEqual(2, self.client.system_handler.raw_process.await_count)
        self.assertNotIn('system-message-id', self.client._message_results)
        self.client.logger.warning.assert_not_called()

    def test_message_result_cache_is_bounded_and_expires(self):
        self.client.MAX_CACHED_MESSAGE_RESULTS = 3
        ack = AckMessage()
        ack.code = AckMessage.STATUS_OK
        ack.message = 'OK'

        with mock.patch('dingtalk_stream.stream.time.monotonic', return_value=100):
            for index in range(5):
                self.client._cache_message_result(
                    'message-%d' % index,
                    '',
                    ack,
                )

        self.assertEqual(
            ['message-2', 'message-3', 'message-4'],
            list(self.client._message_results),
        )
        with mock.patch(
                'dingtalk_stream.stream.time.monotonic',
                return_value=100 + self.client.MESSAGE_RESULT_TTL_SECONDS + 1):
            self.assertIsNone(
                self.client._get_cached_message_result('message-4'),
            )
        self.assertNotIn('message-4', self.client._message_results)

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
