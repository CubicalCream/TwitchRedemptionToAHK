import asyncio
import collections
import random
import subprocess
import threading
import time
from dotenv import dotenv_values
import requests
import json
import signal
import sys
import websockets
from websockets.exceptions import ConnectionClosed
from websockets.frames import Close

# Import AHK paths
import scripts

# Define AuthorizationError
# this is only used in the case that twitch unauthorizes this app, which ideally shouldn't happen
class AuthorizationError(Exception):
    pass

# Import values from .env
config = dotenv_values()
CLIENT_ID:str      = config["client_id"]      # type: ignore
ACCESS_TOKEN:str   = config["ACCESS_TOKEN"]   # type: ignore
CLIENT_SECRET:str  = config["CLIENT_SECRET"]  # type: ignore
REFRESH_TOKEN:str  = config["REFRESH_TOKEN"]  # type: ignore
USER_ID: str

# Declare a deque to store token and user id tuples
# Whenever the token is revalidated, this is cleared and replaced with the newest token
token_deque = collections.deque()

# Get new user token using refresh token
def _get_token():
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type':'refresh_token',
            'refresh_token': REFRESH_TOKEN}
    try:
        response = requests.post('https://id.twitch.tv/oauth2/token', data=data, headers=headers)
    except:
        raise
    
    if (response.ok):
        print('Token refresh OK')
        data = response.json()
        NEW_TOKEN = data["access_token"]
        print(f'refreshed token: {NEW_TOKEN}')
        return _validate(NEW_TOKEN)
    else:
        raise Exception('token refresh failed')

# Validate user token
def _validate(token=None):
    try:
        response = requests.get(
            'https://id.twitch.tv/oauth2/validate',
            headers={
                'Authorization': f'OAuth {ACCESS_TOKEN if token == None else token}'
            }
        )
    except:
        raise

    if (response.ok):
        # If token is valid, set the appropriate vars and return
        print('Token OK')
        data = response.json()
        USER_ID = data["user_id"]
        return ACCESS_TOKEN if token == None else token, USER_ID
    if (response.status_code == 401):
        # If token is invalid, get a new one
        print(f'Token validation failed with 401: {response.text}')
        print('Refreshing user token...')
        return _get_token()
    else:
        print(f'Token validation failed with {response.status_code}: {response.text}')
        raise Exception("Unknown token verification error")

# Generate random* strings for use in communication with Twitch
# Basically a nonce guarantees that the server who responds is the same server you spoke to
def nonce(length):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

# Method to be run in token_validation thread
# Validate with either .env or current token, then run again in an hour*
def token_validation():
    while True:
        try:
            if (len(token_deque) == 0):
                token_tuple = _validate()
            else:
                CURRENT_TOKEN, USER_ID = token_deque[0]
                token_tuple = _validate(token=CURRENT_TOKEN)
        except:
            raise
        else:
            if (len(token_deque) > 0):
                token_deque.pop()
            token_deque.appendleft(token_tuple)
            # *Spec requires an hour, but I'm scared so do it a bit sooner :D
            time.sleep(3500+(random.random()*60))

# Method to be run in ping_thread thread
# Send ping, exit if required, run again in three minutes*
def repeat_ping(ws):
    while True:
        try:
            asyncio.run(_ping(ws))
        except SystemExit:
            sys.exit(0)
        except:
            raise
        else:
            # *Spec requires 5
            time.sleep(180+(random.random()*5))

# Asyncronously run the ping, exit if required
async def _ping(ws):
    try:
        await ws.send('{"type": "PING"}')
        print('>>> {"type": "PING"}')
        # print(f'<<< {await ws.recv()}')
        # TODO: wait for a {"type": "PONG"} response, if there is none within 10 seconds, attempt to reconnect with exponential backoff.
    except SystemExit:
            sys.exit(0)
    except:
        raise

# Subscribe to specified topics
async def subscribe(ws, topics:list, token:str):
    message = {
        'type': 'LISTEN',
        'nonce': nonce(15),
        'data': {
            'topics': topics,
            'auth_token': token
        }
    }
    try:
        await ws.send(json.dumps(message))
        print(f'>>> {json.dumps(message)}')
        # TODO: wait for a {"type": "PONG"} response, if there is none within 10 seconds, attempt to reconnect, with exponential backoff.
    except:
        raise

# Callback to consume messages recieved from the WebSocket
async def consume(message):
    data = json.loads(message)
    excerpt_length = 222
    print(f'\n<<< {message if len(message) < excerpt_length else f" {message[:excerpt_length]} ... plus {len(message)-excerpt_length} more characters"}')
    
    match data["type"]:
        case "PONG":
            pass
        case "MESSAGE":
            message = json.loads(data["data"]["message"])
            if (message["type"] == "reward-redeemed"):
                await redemption_callback(message["data"])
        case "RECONNECT":
            print('Reconnect message recieved, closing current connection...')
            raise ConnectionClosed(Close(1000, 'Reconnect'), None) #type: ignore
            # FIXME This is incredibly weird and probably not good practice...
            # I guess we'll see if it works
        case "AUTH_REVOKED":
            print('Authorization revoked, closing process...')
            raise AuthorizationError

# Callback to run when the recieved message indicates a reward was redeemed
async def redemption_callback(data: dict) -> None:
    rewardId = data['redemption']['reward']['id']
    rewardTitle = data['redemption']['reward']['title']
    redemptionUser = data['redemption']['user']['display_name']
    print(f'\n"{rewardTitle}" ({rewardId}) redeemed by "{redemptionUser}"')

    if (rewardId in scripts.paths):
        scriptPath = scripts.paths[rewardId]
        print(f'Running "{scriptPath}" from "{rewardTitle}"...')
        #              C:/path/to/ahk.exe
        #              ^                      > ./ahk/script.ahk
        subprocess.run([scripts.paths['ahk'], scriptPath])
        # See scripts.py for explanation of syntax

# Start the thing
async def main():

    # Validate token on start
    print('Validating token...')
    validate_thread = threading.Thread(target=token_validation, daemon=True)
    validate_thread.start()
    # Wait for first validation to clear
    while len(token_deque) == 0:
        time.sleep(1)
    CURRENT_TOKEN, USER_ID = token_deque[0]
    print(f'Using User id: {USER_ID}')

    pubsub_uri = 'wss://pubsub-edge.twitch.tv'
    # Establish a connection to Twitch
    # async for ... will automatically reconnect if the connection fails
    # https://websockets.readthedocs.io/en/stable/faq/client.html#how-do-i-reconnect-when-the-connection-drops
    async for websocket in websockets.connect(pubsub_uri, ssl=True): # type: ignore
        try:
            print('\nOpening websocket connection...')
            
            # Schedule pings every 3 minutes
            print('\nSending opening ping...')
            ping_thread = threading.Thread(target=repeat_ping, args=(websocket,), daemon=True)
            ping_thread.start()
            
            # Subscribe to point redemptions on the user's channel
            print("\nSubscribing to point redemptions...")
            await subscribe(websocket, [f'channel-points-channel-v1.{USER_ID}'], CURRENT_TOKEN)

            # WebSocket message consumer
            # See https://websockets.readthedocs.io/en/stable/howto/patterns.html#consumer
            async for message in websocket:
                await consume(message)
            
        # If the connection is closed, continue through the iterable returned from websockets.connect() and try again
        except websockets.ConnectionClosed: # type: ignore
            continue
        except AuthorizationError:
            sys.exit(0)
        except SystemExit:
            sys.exit(0)
        except:
            raise

# CTRLC
def sigint_handler(sig, frame):
    print('Shutting down from Ctrl+C...')
    sys.exit(0)
signal.signal(signal.SIGINT, sigint_handler)

if (__name__ == "__main__"):
    asyncio.run(main())