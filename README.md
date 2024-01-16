# DingTalk Stream Mode 介绍

Python SDK for DingTalk Stream Mode API, Compared with the webhook mode, it is easier to access the DingTalk chatbot

钉钉支持 Stream 模式接入事件推送、机器人收消息以及卡片回调，该 SDK 实现了 Stream 模式。相比 Webhook 模式，Stream 模式可以更简单的接入各类事件和回调。

## 开发教程

在 [教程文档](https://opensource.dingtalk.com/developerpedia/docs/explore/tutorials/stream/overview) 中，你可以找到钉钉 Stream 模式的教程文档和示例代码。

## 特别说明

因拼写错误，从旧版本升级到 v0.13.0 时候，需要将 register_callback_hanlder 修改为 register_callback_handler

### 参考资料

* [Stream 模式说明](https://opensource.dingtalk.com/developerpedia/docs/learn/stream/overview)
* [教程文档](https://opensource.dingtalk.com/developerpedia/docs/explore/tutorials/stream/overview)
* [常见问题](https://opensource.dingtalk.com/developerpedia/docs/learn/stream/faq)
* [Stream 模式共创群](https://opensource.dingtalk.com/developerpedia/docs/explore/support/?via=moon-group)
