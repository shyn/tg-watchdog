import json
import urllib.request


def post(url, payload):
    data = json.dumps(payload)

    req = urllib.request.Request(url=url, data=data.encode("utf-8"), method ="POST")

    # Add the appropriate header.
    req.add_header("Content-type", "application/json; charset=UTF-8")

    with urllib.request.urlopen(req) as resp:
        response_data = json.loads(resp.read().decode("utf-8"))
    return response_data


def get(url):
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))


def verify_captcha(key, solution):
    resp = post("https://api.friendlycaptcha.com/api/v1/siteverify", {
        "solution": solution,
        "secret": key
    })
    if resp['success']:
        return True
    return False
