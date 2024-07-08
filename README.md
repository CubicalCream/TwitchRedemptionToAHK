# TwitchRedemptionToAHK

Simple Twitch app to run configurable AHK scripts when channel point rewards are redeemed

Originally written for [CubicalCream](https://twitch.tv/cubicalcream) (ttv) by [0x0079](https://github.com/0x0079/) (gh).

Only tested on Python 3.11

Usage instructions
- `git clone https://github.com/CubicalCream/TwitchRedemptionToAHK.git`
- `cd TwitchRedemptionToAHK`
- Use a venv (optional but recommended)
  - see https://docs.python.org/3/library/venv.html
  - `python -m venv ./`
  - `./Scripts/activate` or your system's equivalent
  - `deactivate` at any time to leave the venv
- `python -m pip install -r requirements.txt`
- Create a Twitch app and obtain:
  - `Client ID`, `Client Secret`, `Access Token`, `Refresh Token`
  - I'll write more verbose steps later
  - The easiest method is to use the Twitch CLI
- Remove '_sample' from .env and scripts
- Populate .env and scripts.py values appropriately
- `python ./main.py`
- Redeem appropriate rewards to log IDs
- Add reward IDs and paths to `scripts.py`
- `python ./main.py`
