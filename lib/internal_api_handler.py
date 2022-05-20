# Communicate to Flask GUI via internal API
# LEGACY CODE

import requests

def update_status_msg():
    # update the status message in the flask gui
    url = 'http://localhost:5000/api/status'
    data = {'msg': 'test'}
    requests.post(url, json=data)