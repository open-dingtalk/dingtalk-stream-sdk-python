# DingTalk Stream Mode 介绍

Python SDK for DingTalk Stream Mode API, Compared with the webhook mode, it is easier to access the DingTalk chatbot

钉钉支持 Stream 模式接入事件推送、机器人收消息以及卡片回调，该 SDK 实现了 Stream 模式。相比 Webhook 模式，Stream 模式可以更简单的接入各类事件和回调。

## 快速开始

### 准备工作

* Python3 开发环境，https://www.python.org/
* 钉钉开发者账号，具备创建企业内部应用的权限，详见[成为钉钉开发者](https://open.dingtalk.com/document/orgapp/become-a-dingtalk-developer)

### 快速开始指南

1、安装 dingtalk-stream

```Shell
pip3 install dingtalk-stream
```

2、创建企业内部应用

进入[钉钉开发者后台](https://open-dev.dingtalk.com/)，创建企业内部应用，获取ClientID（即 AppKey）和ClientSecret（ 即AppSecret）。

发布应用：在开发者后台左侧导航中，点击“版本管理与发布”，点击“确认发布”，并在接下来的可见范围设置中，选择“全部员工”，或者按需选择部分员工。


3、Stream 模式的机器人（可选）

如果不需要使用机器人功能的话，可以不用创建。

在应用管理的左侧导航中，选择“消息推送”，打开机器人能力，设置机器人基本信息。

注意：消息接收模式中，选择 “Stream 模式”

![Stream 模式](https://img.alicdn.com/imgextra/i3/O1CN01XL4piO1lkYX2F6sW6_!!6000000004857-0-tps-896-522.jpg)

点击“点击调试”按钮，可以创建测试群进行测试。

项目中提供了两个关于机器人的测试案例：

3.1 CalcBot

将用户输入的内容进行数学表达式计算，并以文本消息的方式返回计算结果。

启动服务：
```Shell
cd examples/calcbot
python3 calcbot.py --client_id "put-your-client-id-here" --client_secret "put-your-client-secret-here"
```

测试效果：
![calcbot](https://s1.ax1x.com/2023/05/16/p92jjIJ.png)

3.2 CardBot

接收用户输入，返回一张互动卡片，随后更新卡片的文本和图片内容。

启动服务：
```Shell
cd examples/cardbot
python3 cardbot.py --client_id "put-your-client-id-here" --client_secret "put-your-client-secret-here"
```

测试效果：
![cardbot](https://img.alicdn.com/imgextra/i2/O1CN012Va01a24FOHrQQnWy_!!6000000007361-0-tps-2184-1296.jpg)



### 事件订阅切换到 Stream 模式（可选）

进入钉钉开发者后台，选择企业内部应用，在应用管理的左侧导航中，选择“事件与回调”。
“订阅管理”中，“推送方式”选项中，选择 “Stream 模式”，并保存


### 技术支持

可以搜索共创群，答疑交流。共创群ID：35365014813 （钉钉搜索群号入群）；

也可以扫码入群：

![扫码入群](https://gw.alicdn.com/imgextra/i1/O1CN01Cl10lw1OrfW9LdIgQ_!!6000000001759-0-tps-585-765.jpg)
