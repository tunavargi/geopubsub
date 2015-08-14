import json
import requests

SLOOP_APP_KEY = 'cdc4cf2cd170233f12a9b1'
SLOOP_APP_TOKEN = '123456788'

SLOOP_SERVER_DOMAIN = "http://pushserver.hipo.biz:8193"
SLOOP_DEVICE_TOKEN_PATH_TEMPLATE = "/application/%s/device/notify"


class Device(object):

    token = None
    device_type = None

    def __init__(self, token, device_type):
        self.token = token
        self.device_type = device_type

    def get_badge_count(self):
        """
        A placeholder for the badge count calculations
        """
        return 0

    def get_extra_data(self, extra_data):
        """
        A placeholder for the extra push data.
        """
        return extra_data

    def prepare_message(self, message):
        """
        Prepares message before sending.
        """
        return message

    def process_sloop_response(self, data):
        """
        Process the message coming from sloop
        """
        pass

    def get_server_call_url(self):
        """
        Generates the url for the server call
        """
        sloop_server_domain = SLOOP_SERVER_DOMAIN
        sloop_device_token_path_template = SLOOP_DEVICE_TOKEN_PATH_TEMPLATE
        url = sloop_server_domain + sloop_device_token_path_template % SLOOP_APP_KEY
        url = url + "?token=" + SLOOP_APP_TOKEN

        return url

    def send_push_notification(self, message, url=None, sound=None, extra=None, category=None, *args, **kwargs):
        """
        Sends push message using device token
        """
        extra_data = self.get_extra_data(extra)
        if url:
            extra_data["url"] = url

        data = {
            'device_token': self.token,
            'device_type': self.device_type,
            'alert': self.prepare_message(message),
            'sound': sound,
            'custom': extra_data,
            'badge': self.get_badge_count(),
            'category': category
        }
        data.update(kwargs)
        self._send_payload(data)
        return True

    def send_silent_push_notification(self, extra, content_available, *args, **kwargs):
        extra_data = self.get_extra_data(extra)

        data = {
            'device_token': self.token,
            'device_type': self.device_type,
            'content-available': content_available,
            'sound': '',
            'badge': self.get_badge_count(),
            'custom': extra_data
        }
        data.update(kwargs)
        self._send_payload(data)
        return True

    def _send_payload(self, data):
        headers = {'content-type': 'application/json'}
        r = requests.post(self.get_server_call_url(), data=json.dumps(data), headers=headers)
        r.raise_for_status()
        self.process_sloop_response(r.json())