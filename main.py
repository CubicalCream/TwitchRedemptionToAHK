import subprocess
from twitchAPI.twitch import Twitch
from twitchAPI.oauth  import UserAuthenticator
from twitchAPI.types  import AuthScope
from twitchAPI.helper import first
from twitchAPI.pubsub import PubSub
from dotenv import dotenv_values
import asyncio
from uuid import UUID
from pprint import pprint

# import script paths
import scripts

# import values from .env
config = dotenv_values('.env')
CLIENT_ID:str      = config['CLIENT_ID']      # type: ignore
CLIENT_SECRET:str  = config['CLIENT_SECRET']  # type: ignore
TARGET_CHANNEL:str = config['TARGET_CHANNEL'] # type: ignore

    # callback to run when a reward is redeemed
async def redemption_callback(uuid: UUID, data: dict) -> None:

    # good fucking lord python why are you like this
    # i think the data['data'] is twich's fault
    # but this would look so much better if it was in js
    # console.log(`"${data.redemption.reward.title}" redeemed by "${data.redemption.user.display_name}"`)
    # im just sayin
    rewardId = data['data']['redemption']['reward']['id']
    rewardTitle = data['data']['redemption']['reward']['title']
    redemptionUser = data['data']['redemption']['user']['display_name']
    print(f'\n"{rewardTitle}" ({rewardId}) redeemed by "{redemptionUser}"')
    # optionally pretty print the complete response
    # pprint(data)

    if (rewardId in scripts.paths):
        scriptPath = scripts.paths[rewardId]
        print(f'Running "{scriptPath}" from "{rewardTitle}"...')
        subprocess.run([scripts.paths['ahk'], scriptPath])

    # Start the thing
async def startApp():
    twitch = await Twitch(CLIENT_ID, CLIENT_SECRET)

    target_scope = [AuthScope.CHANNEL_READ_REDEMPTIONS]
    auth = UserAuthenticator(twitch, target_scope, force_verify=False)
    # this will open your default browser and prompt you with the twitch verification website
    token, refresh_token = await auth.authenticate() # type: ignore
    # add User authentication
    await twitch.set_user_authentication(token, target_scope, refresh_token)
    user = await first(twitch.get_users(logins=[TARGET_CHANNEL]))
    # TODO: use user token from .env probably

    # Setting up pubsub
    pubsub = PubSub(twitch)
    pubsub.start()
    # Listen to point redemptions
    pointRedemptions = await pubsub.listen_channel_points(user.id, redemption_callback) # type: ignore

    # wait to close the program
    input('\n At any point press ENTER to close...\n')
    await pubsub.unlisten(pointRedemptions)
    pubsub.stop()
    await twitch.close()

asyncio.run(startApp())