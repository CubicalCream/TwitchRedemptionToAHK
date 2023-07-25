docs
- [twitch](https://dev.twitch.tv/docs/api/)
- [twitch cli](https://dev.twitch.tv/docs/cli/)
- [twitch auth](https://dev.twitch.tv/docs/authentication/)
- [twitch pubsub](https://dev.twitch.tv/docs/pubsub/)

usecase
- configurable mappings between rewards and scripts
```py
paths = {
    'ahk': 'C:/Users/Eric/AppData/Local/Programs/AutoHotkey/v2/AutoHotkey64.exe',
    #  /> twitch redemption id                  /> path to ahk script
    '85f92ee0-ba16-4d69-b049-1b9062fbfbd4': './ahk/ROTMG/SoundTesting.ahk',
}
```

flow
- start app
- use `client_id` and `client_secret` to get `access_token` and `refresh_token`
  - `channel:read:redemptions` scope
  - this requires a full oauth client
  - for now, just load `access_token` and `refresh_token` from .env
- check if user refresh is needed
- if yes, refresh user token
- get target user id
- subscribe to `channel-points-channel-v1.<channel_id>` pubsub topic
- when a redemption message is recieved, call redemption_callback
- close app when needed