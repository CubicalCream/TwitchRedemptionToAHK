import asyncio
import random
import subprocess
from dotenv import dotenv_values
import requests
import json
import signal
import sys
import websockets
from websockets.exceptions import ConnectionClosed
from websockets.frames import Close

# Configure logging
# This is used by both WebSockets and Requests
import logging
logging.basicConfig(
    format="%(message)s",
    level=logging.DEBUG,
)

# import script paths
import scripts

# define AuthorizationError
# this is only used in the case that twitch unauthorizes this app, which ideally shouldn't happen
class AuthorizationError(Exception):
    pass

# import values from .env
config = dotenv_values()
CLIENT_ID:str      = config["client_id"]      # type: ignore
ACCESS_TOKEN:str   = config["ACCESS_TOKEN"]   # type: ignore
CLIENT_SECRET:str  = config["CLIENT_SECRET"]  # type: ignore
REFRESH_TOKEN:str  = config["REFRESH_TOKEN"]  # type: ignore
USER_ID: str

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
        print('Token OK')
        data = response.json()
        USER_ID = data["user_id"]
        return ACCESS_TOKEN if token == None else token, USER_ID
    if (response.status_code == 401):
        print(f'Token validation failed with 401: {response.text}')
        print('Refreshing user token...')
        return _get_token()
    else:
        print(f'Token validation failed with {response.status_code}: {response.text}')
        raise Exception("Unknown token verification error")

# Generate random* strings for use in communication with Twitch
def nonce(length):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

# Schedule token_validation() to be run in an hour*, and return the value of validate()
def token_validation(loop:asyncio.AbstractEventLoop):
    try:
        new_token = _validate()
    except:
        raise
    else:
        loop.call_later(3500, token_validation, loop)
        return new_token

# Schedule repeat_ping() to be run in 3 minutes, and ping twitch to keep the websocket open
async def repeat_ping(loop:asyncio.AbstractEventLoop, ws):
    try:
        await ws.send('{"type": "PING"}')
        # await ws.ping()
        print('>>> {"type": "PING"}')
        print(f'<<< {await ws.recv()}')
        # TODO: wait for a {"type": "PONG"} response, if there is none within 10 seconds, attempt to reconnect, with exponential backoff.
    except:
        raise
    else:        
        loop.call_later((180+(random.random()*5)), repeat_ping, loop, ws)

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

# callback to consume message from WebSocket
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
            raise ConnectionClosed(Close(1000, 'Reconnect'), None)
            # This is incredibly weird and probably not good practice...
            # I guess we'll see if it works
        case "AUTH_REVOKED":
            print('Authorization revoked, closing process...')
            raise AuthorizationError

# callback to run when a reward is redeemed
async def redemption_callback(data: dict) -> None:
    rewardId = data['redemption']['reward']['id']
    rewardTitle = data['redemption']['reward']['title']
    redemptionUser = data['redemption']['user']['display_name']
    print(f'\n"{rewardTitle}" ({rewardId}) redeemed by "{redemptionUser}"')

    if (rewardId in scripts.paths):
        scriptPath = scripts.paths[rewardId]
        print(f'Running "{scriptPath}" from "{rewardTitle}"...')
        # C:/path/to/ahk.exe ./ahk/script.ahk
        subprocess.run([scripts.paths['ahk'], scriptPath])

# Start the thing
async def main():
    loop = asyncio.new_event_loop()

    # Validate token on start
    # TODO make this run every hour in compliance with https://dev.twitch.tv/docs/authentication/validate-tokens/
    print('Validating token...')
    try:
        # Get the up to date token and user ID from twitch
        CURRENT_TOKEN, USER_ID = token_validation(loop)
    except:
        raise
    
    pubsub_uri = 'wss://pubsub-edge.twitch.tv'
    # Establish a connection to Twitch
    # async for ... will automatically reconnect if the connection fails
    # https://websockets.readthedocs.io/en/stable/faq/client.html#how-do-i-reconnect-when-the-connection-drops
    async for websocket in websockets.connect(pubsub_uri, ssl=True): # type: ignore
        try:
            print('Opening websocket connection...\n')
            # Schedule pings every 3 minutes
            await repeat_ping(loop, websocket)
            # Subscribe to point redemptions on the user's channel
            await subscribe(websocket, [f'channel-points-channel-v1.{USER_ID}'], CURRENT_TOKEN)

            # WebSocket message consumer
            # See https://websockets.readthedocs.io/en/stable/howto/patterns.html#consumer
            # TODO This blocks execution of the event loop, figure out how to not do that
            # Otherwise, as far as I can tell, everything is good
            async for message in websocket:
                await consume(message)
            
        # If the connection is closed, continue through the iterable returned from websockets.connect() and try again
        except websockets.ConnectionClosed: # type: ignore
            continue
        except AuthorizationError:
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