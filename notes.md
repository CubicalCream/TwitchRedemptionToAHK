library
- https://pypi.org/project/twitchAPI/
- https://pytwitchapi.readthedocs.io/en/stable/
- https://pytwitchapi.readthedocs.io/en/stable/modules/twitchAPI.eventsub.html#twitchAPI.eventsub.EventSub.listen_channel_points_custom_reward_redemption_add

usecase
- configurable mappings between rewards and scripts
  - my goto is always json but there might be a better approach in python
```
{ 
    "rewardName": "scriptName",
    "rewardName": "scriptName",
    ...
}
```

shit to learn
- how to run ~~ahk scripts~~ EXEs with python
  - ~~EXEs or AHKs?~~