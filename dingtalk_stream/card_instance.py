# -*- coding:utf-8 -*-

"""
这里提供了一些常用的卡片模板及其封装类
"""

from .card_replier import CardReplier, AICardReplier, AICardStatus
import json


class MarkdownCardInstance(CardReplier):
    """
    一款超级通用的markdown卡片
    """

    def __init__(self, dingtalk_client, incoming_message):
        super(MarkdownCardInstance, self).__init__(dingtalk_client, incoming_message)
        self.card_template_id = "589420e2-c1e2-46ef-a5ed-b8728e654da9.schema"
        self.card_instance_id = None
        self.title = None
        self.logo = None

    def set_title_and_logo(self, title: str, logo: str):
        self.title = title
        self.logo = logo

    def _get_card_data(self, markdown) -> dict:
        card_data = {
            "markdown": markdown,
        }

        if self.title is not None and self.title != "":
            card_data["title"] = self.title

        if self.logo is not None and self.logo != "":
            card_data["logo"] = self.logo

        return card_data

    def reply(self, markdown: str, at_sender: bool = False, at_all: bool = False):
        """
        回复markdown内容
        :param markdown:
        :param title:
        :param logo:
        :param at_sender:
        :param at_all:
        :return:
        """
        self.card_instance_id = self.create_and_send_card(self.card_template_id, self._get_card_data(markdown),
                                                          at_sender=at_sender, at_all=at_all)

    def update(self, markdown: str):
        """
        更新markdown内容，如果你reply了多次，这里只会更新最后一张卡片
        :param markdown:
        :return:
        """
        if self.card_instance_id is None or self.card_instance_id == "":
            self.logger.error('MarkdownCardInstance.update failed, you should send card first.')
            return

        self.put_card_data(self.card_instance_id, self._get_card_data(markdown))


class AIMarkdownCardInstance(AICardReplier):
    """
    一款超级通用的AI Markdown卡片
    ai_start --> ai_streaming --> ai_streaming --> ai_finish/ai_fail
    """

    def __init__(self, dingtalk_client, incoming_message):
        super(AIMarkdownCardInstance, self).__init__(dingtalk_client, incoming_message)
        self.card_template_id = "382e4302-551d-4880-bf29-a30acfab2e71.schema"
        self.card_instance_id = None
        self.title = None
        self.logo = None
        self.markdown = ""
        self.inputing_status = False

    def set_title_and_logo(self, title: str, logo: str):
        self.title = title
        self.logo = logo

    def ai_start(self):
        """
        开始执行中
        :return:
        """
        self.card_instance_id = self.start(self.card_template_id, {})
        self.inputing_status = False

    def ai_streaming(self, markdown: str, append: bool = False):
        """
        打字机模式
        :param append: 两种更新模式，append=true，追加的方式；append=false，全量替换。
        :param markdown:
        :return:
        """
        if self.card_instance_id is None or self.card_instance_id == "":
            self.logger.error('AIMarkdownCardInstance.ai_streaming failed, you should send card first.')
            return

        if not self.inputing_status:
            card_data = {
                "flowStatus": AICardStatus.INPUTING,
                "msgContent": ""
            }

            if self.title is not None and self.title != "":
                card_data["msgTitle"] = self.title

            if self.logo is not None and self.logo != "":
                card_data["logo"] = self.logo

            order = [
                "msgTitle",
                "msgButtons",
                "msgImages",
                "msgTextList",
                "msgContent"
            ]

            card_data["sys_full_json_obj"] = json.dumps({"order": order})

            self.put_card_data(self.card_instance_id, card_data)

            self.inputing_status = True

        if append:
            self.markdown = self.markdown + markdown
        else:
            self.markdown = markdown

        self.streaming(self.card_instance_id, "msgContent", self.markdown, append=False, finished=False,
                       failed=False)

    def ai_finish(self, markdown: str = ""):
        """
        完成态
        :param markdown:
        :return:
        """
        if self.card_instance_id is None or self.card_instance_id == "":
            self.logger.error('AIMarkdownCardInstance.ai_finish failed, you should send card first.')
            return

        if markdown == "" or markdown is None:
            markdown = self.markdown
        else:
            self.markdown = markdown

        order = [
            "msgTitle",
            "msgButtons",
            "msgImages",
            "msgTextList",
            "msgContent"
        ]

        card_data = {
            "msgContent": markdown,
            "sys_full_json_obj": json.dumps({"order": order})
        }

        if self.title is not None and self.title != "":
            card_data["msgTitle"] = self.title

        if self.logo is not None and self.logo != "":
            card_data["logo"] = self.logo

        self.finish(self.card_instance_id, card_data)

    def ai_fail(self):
        """
        失败态
        :return:
        """

        if self.card_instance_id is None or self.card_instance_id == "":
            self.logger.error('AIMarkdownCardInstance.ai_fail failed, you should send card first.')
            return

        card_data = {}

        if self.title is not None and self.title != "":
            card_data["msgTitle"] = self.title

        if self.logo is not None and self.logo != "":
            card_data["logo"] = self.logo

        self.fail(self.card_instance_id, card_data)


class CarouselCardInstance(AICardReplier):
    """
    轮播图卡片
    """

    def __init__(self, dingtalk_client, incoming_message):
        super(CarouselCardInstance, self).__init__(dingtalk_client, incoming_message)
        self.card_template_id = "382e4302-551d-4880-bf29-a30acfab2e71.schema"
        self.card_instance_id = None
        self.title = None
        self.logo = None

    def set_title_and_logo(self, title: str, logo: str):
        self.title = title
        self.logo = logo

    def ai_start(self):
        """
        开始执行中
        :return:
        """
        self.card_instance_id = self.start(self.card_template_id, {})

    def reply(self, markdown: str, image_slider_list: list, button_text: str = "submit"):
        """
        回复卡片
        :param button_text:
        :param image_slider_list:
        :param markdown:
        :return:
        """

        sys_full_json_obj = {
            "order": [
                "msgTitle",
                "msgMarkdown",
                "msgSlider",
                "msgImages",
                "msgTextList",
                "msgButtons",
            ],
            "msgSlider": [],
            "msgButtons": [
                {
                    "text": button_text,
                    "color": "blue",
                    "id": "image_slider_select_button",
                    "request": True
                }
            ]
        }

        if button_text is not None and button_text!="":
            sys_full_json_obj["msgButtons"][0]["text"] = button_text

        for image_slider in image_slider_list:
            sys_full_json_obj["msgSlider"].append({
                "title": image_slider[0],
                "image": image_slider[1]
            })

        card_data = {
            "msgMarkdown": markdown,
            "sys_full_json_obj": json.dumps(sys_full_json_obj)
        }

        if self.title is not None and self.title != "":
            card_data["msgTitle"] = self.title

        if self.logo is not None and self.logo != "":
            card_data["logo"] = self.logo

        self.card_instance_id = self.create_and_send_card(self.card_template_id,
                                                          {"flowStatus": AICardStatus.PROCESSING},
                                                          callback_type="STREAM")

        self.finish(self.card_instance_id, card_data)
