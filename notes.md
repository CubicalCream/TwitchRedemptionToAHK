library
- https://pypi.org/project/twitchAPI/
- [docs](https://pytwitchapi.readthedocs.io/en/stable/)
- [docs - point rewards](https://pytwitchapi.readthedocs.io/en/stable/modules/twitchAPI.eventsub.html#twitchAPI.eventsub.EventSub.listen_channel_points_custom_reward_redemption_add)

docs
- [twitch](https://dev.twitch.tv/docs/api/)
- [twitch cli](https://dev.twitch.tv/docs/cli/)
- [twitch auth](https://dev.twitch.tv/docs/authentication/)

usecase
- configurable mappings between rewards and scripts
```py
paths = {
    'ahk': 'C:/Users/Eric/AppData/Local/Programs/AutoHotkey/v2/AutoHotkey64.exe',
    # ⮫ twitch redemption id                  ⮫ path to ahk script
    '85f92ee0-ba16-4d69-b049-1b9062fbfbd4': './ahk/ROTMG/SoundTesting.ahk',
}
```