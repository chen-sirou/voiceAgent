import requests
import json


class WeChatSender:

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_registration(self, registration: dict):

        text = (
            "【园区来客登记】\n\n"
            f"车牌号：{registration.get('plate_number')}\n"
            f"来访单位：{registration.get('target_company')}\n"
            f"手机号：{registration.get('phone')}\n"
            f"来访事由：{registration.get('visit_reason')}\n"
            f"入场时间：{registration.get('entry_time')}"
        )

        payload = {
            "msgtype": "text",
            "text": {
                "content": text
            }
        }

        response = requests.post(
            self.webhook_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload)
        )

        print("微信发送结果:", response.text)