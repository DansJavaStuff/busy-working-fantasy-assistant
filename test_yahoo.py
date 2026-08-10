import json
from pathlib import Path

import requests

TOKEN_FILE = Path("yahoo_token.json")

token_data = json.loads(TOKEN_FILE.read_text())
access_token = token_data["access_token"]

url = (
    "https://fantasysports.yahooapis.com/"
    "fantasy/v2/users;use_login=1/games;game_codes=nfl/leagues"
)

headers = {
    "Authorization": f"Bearer {access_token}"
}

params = {
    "format": "json"
}

response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=30
)

print("HTTP status:", response.status_code)

if response.ok:
    data = response.json()

    print()
    print("SUCCESS!")
    print()
    print(json.dumps(data, indent=2))

else:
    print()
    print("Yahoo returned an error:")
    print(response.text)
