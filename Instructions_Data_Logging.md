# QST-Dash
U of S QST Dash Code 

**Pi Boot UP**
The 2024-2025 Tractor Dash runs off the **crontab** for initial bootup
* For Editing puroses use crontab -e
* Below is the current code used to run the file on reboot of the pi
@reboot sleep 3 &&  export XDG_RUNTIME_DIR=/run/user/$(id -u) && /usr/bin/python3 /home/qst/Desktop/Digital-Tractor-Dash/Tractor_Dash_Experimental.py >> /home/qst/Desk>

Last Date of **Pi Boot Up** update:
Oct 25th, 2025
Dillan & Graden
