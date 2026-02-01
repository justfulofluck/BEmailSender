import json
import os

SETTINGS_FILE = 'email_settings.json'

def save_email_settings(settings: dict):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

def load_email_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return None
