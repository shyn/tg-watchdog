tg-watchdog in python

Quick implemented in python and inspired by https://github.com/Astrian/tg-watchdog 

[![Deploy](https://button.deta.dev/1/svg)](https://go.deta.dev/deploy?repo=https://github.com/shyn/tg-watchdog)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template/HhsNQ-?referralCode=uL9pZG)

## Features

- Easy to self-host
- Easy deploy to PaaS platforms like [deta](https://deta.sh) and [Railway](https://railway.app)
- Do not disturb your group members. No in group captcha. No join message.

## Deployment

### Railway (Recommend)
- Just click the deploy button above!

### Self-host

- Change `env-example` to `.env`
- Config your tokens and keys in .env file
- Run the flask app :)

### Free deta host

- Change `env-example` to `.env`
- Config your tokens and keys in .env file
- run `deta update -e .env` to update project environments
- Click to deta button or just run `deta deploy`
