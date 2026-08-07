# !/usr/bin/env python

import argparse
import logging
from dingtalk_stream import AckMessage
import dingtalk_stream


def setup_logger():
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('%(asctime)s %(name)-8s %(levelname)-8s %(message)s [%(filename)s:%(lineno)d]'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def define_options():
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


class FileBotHandler(dingtalk_stream.ChatbotHandler):
    def __init__(self, logger: logging.Logger = None):
        super(dingtalk_stream.ChatbotHandler, self).__init__()
        if logger:
            self.logger = logger

    async def process(self, callback: dingtalk_stream.CallbackMessage):
        incoming_message = dingtalk_stream.ChatbotMessage.from_dict(callback.data)
        if incoming_message.message_type not in ('file', 'audio', 'video'):
            return AckMessage.STATUS_OK, 'OK'

        download_codes = None
        if incoming_message.message_type == 'file':
            download_codes = incoming_message.get_file_list()
        elif incoming_message.message_type == 'audio':
            download_codes = incoming_message.get_audio_list()
        else:
            download_codes = incoming_message.get_video_list()

        lines = []
        if incoming_message.message_type == 'file':
            if incoming_message.file_content is not None and incoming_message.file_content.file_name:
                lines.append('File: %s' % incoming_message.file_content.file_name)
            else:
                lines.append('File received')
        elif incoming_message.message_type == 'audio':
            lines.append('Audio received')
            if incoming_message.audio_content is not None:
                if incoming_message.audio_content.duration is not None:
                    lines.append('Duration: %s' % incoming_message.audio_content.duration)
                if incoming_message.audio_content.recognition:
                    lines.append('Recognition: %s' % incoming_message.audio_content.recognition)
        else:
            lines.append('Video received')
            if incoming_message.video_content is not None:
                if incoming_message.video_content.duration is not None:
                    lines.append('Duration: %s' % incoming_message.video_content.duration)
                if incoming_message.video_content.video_type:
                    lines.append('Video Type: %s' % incoming_message.video_content.video_type)

        if download_codes:
            download_urls = []
            for download_code in download_codes:
                download_url = self.get_file_download_url(download_code)
                if download_url:
                    self.logger.info('%s download url: %s', incoming_message.message_type, download_url)
                    download_urls.append(download_url)

            if download_urls:
                if len(download_urls) == 1:
                    lines.append('Download URL: %s' % download_urls[0])
                else:
                    lines.append('Download URLs:')
                    lines.extend(['%d. %s' % (idx + 1, url) for idx, url in enumerate(download_urls)])

        if lines:
            response = '\n'.join(lines)
            self.reply_text(response, incoming_message)

        return AckMessage.STATUS_OK, 'OK'


def main():
    logger = setup_logger()
    options = define_options()

    credential = dingtalk_stream.Credential(options.client_id, options.client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_callback_handler(dingtalk_stream.chatbot.ChatbotMessage.TOPIC, FileBotHandler(logger))
    client.start_forever()


if __name__ == '__main__':
    main()
