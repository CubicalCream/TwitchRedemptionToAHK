import asyncio
import random
import subprocess
from dotenv import dotenv_values
import requests
import json
import signal
import sys
import websockets

# import script paths
import scripts

# import values from .env
config = dotenv_values('.env')
CLIENT_ID:str      = config['CLIENT_ID']      # type: ignore
ACCESS_TOKEN:str   = config['ACCESS_TOKEN']   # type: ignore
CLIENT_SECRET:str  = config['CLIENT_SECRET']  # type: ignore
REFRESH_TOKEN:str  = config['REFRESH_TOKEN']  # type: ignore
TARGET_CHANNEL:str = config['TARGET_CHANNEL'] # type: ignore

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

def token():
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type':'refresh_token',
            'refresh_token': REFRESH_TOKEN}
    response = requests.post('https://id.twitch.tv/oauth2/token', data=data, headers=headers)
    
    if (response.ok):
        print('Token refresh OK')
        return response
    else:
        raise Exception('token refresh failed')

def validate():
    # Validate user token
    response = requests.get(
        'https://id.twitch.tv/oauth2/validate',
        headers={
            'Authorization': f'OAuth {ACCESS_TOKEN}'
        }
    )
    if (response.ok):
        print('Token OK')
        return ACCESS_TOKEN
    if (response.status_code == 401):
        print(f'Token validation failed with 401: {response.text}')
        print('Refreshing user token...')
        return token()

def nonce(length):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

# Start the thing
async def main():
    # Validate token on start
    # TODO make this run every hour in compliance with https://dev.twitch.tv/docs/authentication/validate-tokens/
    print('Validating token...')
    ACCESS_TOKEN = validate()
    
    print('Opening websocket connection...\n')
    ws_uri = 'wss://pubsub-edge.twitch.tv'
    async with websockets.connect(ws_uri, ssl=True) as websocket: # type: ignore
        await websocket.send('{"type": "PING"}')
        print('>>> {"type": "PING"}')
        print(f'<<< {await websocket.recv()}')
        
        message = {
            'type': 'LISTEN',
            'nonce': nonce(15),
            'data': {
                'topics': ['channel-points-channel-v1.95815081'],
                'auth_token': ACCESS_TOKEN
            }
        }

        await websocket.send(json.dumps(message))
        print(f'>>> {json.dumps(message)}')
        
        while True:
            res = await websocket.recv()
            data = json.loads(res)
            excerpt_length = 222
            print(f'\n<<< {res if len(res) < excerpt_length else f" {res[:excerpt_length]} ... plus {len(res)-200} more characters"}')
            # TODO send a ping every minute to keep the connection alive
            # TODO implement connection management
            # https://dev.twitch.tv/docs/pubsub/#connection-management
            if (data["type"] == "MESSAGE"):
                message = json.loads(data["data"]["message"])
                if (message["type"] == "reward-redeemed"):
                    await redemption_callback(message["data"])

# CTRLC
def sigint_handler(sig, frame):
    print('Shutting down from Ctrl+C...')
    sys.exit(0)
signal.signal(signal.SIGINT, sigint_handler)

if (__name__ == "__main__"):
    asyncio.run(main())