from twitchAPI.twitch import Twitch
from twitchAPI.helper import first
from dotenv import dotenv_values

config = dotenv_values('.env')

print('it do be happenin')

twitch = Twitch(config['CLIENT_ID'], config['CLIENT_SECRET'])

print(twitch)