# TwitchRedemptionToAHK

Simple Twitch app to run configurable AHK scripts when channel point rewards are redeemed

Originally written for [CubicalCream](https://twitch.tv/cubicalcream) on twitch

Pytyhon instructions
- 3.11+
- use a venv 🔫
  - see https://docs.python.org/3/library/venv.html
  - `python -m venv ./`
  - `./scripts/activate` or your system's equivalent
  - `python -m pip install -r requirements.txt`

Use instructions
- remove '_sample' from .env and scripts
- replace their contents with the appropriate values
- `python ./main.py`
- login in the tab that opened in your browser
- redeem point rewards in question and add their IDs to `scripts.py` accordingly
- shutdown the bot by pressing enter in the console
  - DONT USE CTRL+C
  - I HAVE NO CLUE WHY BUT IT DOESNT WORK AND I CANT BE BOTHERED TO FIX IT
- restart the bot
- 🚀