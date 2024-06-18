# -*- coding:utf-8 -*-

import os

DINGTALK_OPENAPI_ENDPOINT = "https://api.dingtalk.com"

def get_dingtalk_endpoint():
    endpoint_env = os.getenv('DINGTALK_OPENAPI_ENDPOINT')
    if endpoint_env:
        return endpoint_env
    return DINGTALK_OPENAPI_ENDPOINT
