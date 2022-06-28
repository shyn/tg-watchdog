tg-watchdog in python

Quick implemented in python and inspired by https://github.com/Astrian/tg-watchdog 

[![Deploy](https://button.deta.dev/1/svg)](https://go.deta.dev/deploy?repo=https://github.com/shyn/tg-watchdog)

## Features

- Easy to self-host
- Easy deploy to free SaaS platforms like [deta](https://deta.sh)

## Deployment

### Self-host

- Change `env-example` to `.env`
- Config your tokens and keys in .env file
- Run the flask app :)

### Free deta host

- Change `env-example` to `.env`
- Config your tokens and keys in .env file
- run `deta update -e .env` to update project environments
- Click to deta button or just run `deta deploy`