# syntax here is scripts: { "rewardId": "pathToScript" }
paths = {
    'ahk': 'C:/Users/{You}/AppData/Local/Programs/AutoHotkey/v2/AutoHotkey64.exe',
    'rewardID': './ahk/script.ahk',
}

if (__name__ == "__main__"):
    print("""
This file is not meant to be run as main. Run `main.py` instead.
    This file contains the path to the system's ahk executable and mappings of redemption IDs to AHK scripts.
    
The first key-value pair of paths must always be 'ahk': 'X:/path/to/ahk.exe', any following are in the format 'redemptionID':'path/to/script'.
The AHK path can either be absolute in the case that the app should run the system's installation, or local if ahk.exe is nearby the app's root folder. To find the required redemption IDs, run the app and redeem the necessary redemptions to log their IDs. It is easiest for AHK paths to be local, starting with './ahk/'.
    """)