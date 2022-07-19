import os
import hashlib
import hmac
from flask import Flask, request, render_template

import json
import utils


TG_BOT_TOKEN = os.getenv('BOT_TOKEN')
TG_API = 'https://api.telegram.org/bot'

class TGBot:
    def __init__(self, token):
        self.api = TG_API + token
    
    def _post(self, api_name, payload):
        response_data = utils.post(self.api+'/'+api_name, payload)
        if not response_data['ok']:
            raise Exception(response_data['description']) 
        return response_data['result']
    
    def _get(self, api_name):
        response_data = utils.get(f'{self.api}/{api_name}')
        if not response_data['ok']:
            raise Exception(response_data['description']) 
        return response_data.get('result')

    def setup_webhook(self, webhook_url):
        webhookinfo = self._get('getwebhookinfo')
        if webhookinfo['url']:
            return
        self.set_webhook(webhook_url)

    def set_webhook(self, url):
        return self._post('setWebhook', {'url': url})

    def send_message(self, chat_id, text, **kwargs):
        return self._post('sendMessage', {'chat_id': chat_id, 'text': text, **kwargs})
    
    def approve_chat_join_request(self, chat_id, user_id):
        return self._post('approveChatJoinRequest', {'chat_id': chat_id, 'user_id': user_id})

    def decline_chat_join_request(self, chat_id, user_id):
        return self._post('declineChatJoinRequest', {'chat_id': chat_id, 'user_id': user_id})

    def delete_webhook(self):
        return self._get('deleteWebhook')

    def delete_message(self, chat_id, message_id):
        return self._post('deleteMessage', {'chat_id': chat_id, 'message_id': message_id})

    def edit_message_reply_markup(self, chat_id, message_id, reply_markup):
        return self._post('editMessageReplyMarkup', {'chat_id': chat_id, 'message_id': message_id, 'reply_markup': reply_markup})


class WatchdogHandler:
    messages_to_delete = {
            'new_chat_member', 
            'new_chat_members', 
            'left_chat_member',
            'new_chat_title',
            'new_chat_photo',
            'delete_chat_photo',
            'group_chat_created',
            'subpergroup_chat_created',
            'channel_chat_created',
            'message_auto_delete_timer_changed',
    }

    def __init__(self, bot):
        self._bot = bot

    def handle(self, update):
        from pprint import pprint
        pprint(update)
        if 'chat_join_request' in update:
            self.handle_chat_join_request(update['chat_join_request'])
        elif 'message' in update:
            self.handle_message(update['message'])

    def handle_chat_join_request(self, chat_join_request):
        user_id = chat_join_request['from']['id']
        chat_id = chat_join_request['chat']['id']
        chat_title = chat_join_request['chat']['title']
        ts = int(time.time() * 1000)
        sig = hmac.new(TG_BOT_TOKEN, f'{user_id},{chat_id},{ts}'.encode(), hashlib.sha256).hexdigest()
        msg = self._bot.send_message(
                user_id, 
                f'Welcom to join {chat_title}',
                reply_markup={
                  "inline_keyboard": [[{
                    "text": '开始验证',
                    "web_app": {
                        "url": f"https://{domain}/verify?chat_id={chat_id}&sig={sig}&ts={ts}"
                    }
                  }]]}
            )
        self._bot.edit_message_reply_markup(
                chat_id, 
                msg['message_id'], 
                reply_markup={
                  "inline_keyboard": [[{
                    "text": '开始验证',
                    "web_app": {
                        "url": f"https://{domain}/verify?chat_id={chat_id}&sig={sig}&ts={ts}&msg_id={msg['message_id']}"
                    }
                  }]]}
        )

    def handle_message(self, message):
        if self.messages_to_delete & message.keys():
            self._bot.delete_message(message['chat']['id'], message['message_id'])


def verify_user(data_check_str, hash_str):
    h1 = hmac.new("WebAppData".encode(), TG_BOT_TOKEN.encode(), hashlib.sha256)
    h2 = hmac.new(h1.digest(), data_check_str.encode(), hashlib.sha256)
    return h2.hexdigest() == hash_str


app = Flask(__name__, template_folder='.')
bot = TGBot(TG_BOT_TOKEN)
handler = WatchdogHandler(bot)

if TG_BOT_TOKEN:
    deta_path = os.getenv('DETA_PATH')
    railway_path = os.getenv('RAILWAY_STATIC_URL')
    domain = os.getenv('DOMAIN')
    if not deta_path and not domain and not railway_path:
        raise ValueError("seems like you are not running in deta, set a domain then.")
    if not domain:
        domain = deta_path + '.deta.dev' if deta_path else railway_path
    webhook_url = f'https://{domain}/{os.getenv("WEBHOOK", "webhook")}'
    bot.set_webhook(webhook_url)


@app.route('/')
def index():
    return {'ok': True}


@app.route('/'+os.getenv('WEBHOOK', 'webhook'), methods=['POST', 'GET'])
def tg_webhook_view():
    payload = request.json
    handler.handle(payload)
    if not payload:
        return 'empty request'
    return ''


@app.route('/verify', methods=['GET', 'POST'])
def verify_view():
    if request.method == 'GET':
        chat_id = request.args.get('chat_id')
        sig = request.args.get('sig')
        ts = request.args.get('ts')
        if not chat_id or not sig:
            return "invalid request"
        return render_template('verify.html', chat_id=chat_id, sig=sig, ts=ts, sitekey=os.getenv('FCAPSITEKEY'))
    data = request.json
    user_id = json.loads(data['user'])['id']
    hash_str = data.pop('hash')
    chat_id = data.pop('chat_id')
    solution = data.pop('solution')
    # verify signature
    sig = data.pop('sig')
    ts = data.pop('ts')
    cal_sig = hmac.new(TG_BOT_TOKEN, f'{user_id},{chat_id},{ts}'.encode(), hashlib.sha256).hexdigest()
    if cal_sig != sig:
        return "invalid request", 400

    # check if timeout
    if int(time.time() * 1000) > ts + 180000:
       bot.delete_message(chat_id, msg_id)
       return {'ok': False}

    check_hash_str = '\n'.join(map(lambda item:f'{item[0]}={item[1]}', sorted(data.items())))
    valid_user = verify_user(check_hash_str, hash_str)
    valid_captcha = utils.verify_captcha(os.getenv('FCAPAPIKEY'), solution)
    if valid_user and valid_captcha:
        bot.approve_chat_join_request(chat_id, user_id)
    return {'ok': valid_user and valid_captcha}


if __name__ == '__main__':
    app.run('0.0.0.0', port=os.getenv('PORT'))
