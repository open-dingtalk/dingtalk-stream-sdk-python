#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import asyncio
import dingtalk_stream

def define_options():
    import argparse
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


class HelloHandler(dingtalk_stream.GraphHandler):
    async def process(self, callback: dingtalk_stream.CallbackMessage):
        request = dingtalk_stream.GraphRequest.from_dict(callback.data)
        body = json.loads(request.body)
        await self.reply_markdown(body['sessionWebhook'], '- 天气：晴\n- temperature: 22')
        return dingtalk_stream.AckMessage.STATUS_OK, self.get_success_response({'success': True}).to_dict()

async def hello():
    options = define_options()
    credential = dingtalk_stream.Credential(options.client_id, options.client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_callback_handler(dingtalk_stream.graph.GraphMessage.TOPIC, HelloHandler())
    await client.start()

if __name__ == '__main__':
    asyncio.run(hello())