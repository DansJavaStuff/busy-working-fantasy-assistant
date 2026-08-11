import os
import json

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FANTASYPROS_API_KEY")

if not API_KEY:
    raise RuntimeError("FANTASYPROS_API_KEY is missing from .env")

url = "https://api.fantasypros.com/public/v2/json/nfl/2026/consensus-rankings"

headers = {
    "x-api-key": API_KEY,
}

params = {
    "position": "RB",
    "scoring": "HALF",
}

response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=30,
)

print("HTTP status:", response.status_code)

if response.ok:
    data = response.json()

    print()
    print("SUCCESS!")
    print()

    # Save the complete response locally rather than
    # dumping hundreds of players to the terminal.
    with open("fantasypros_test.json", "w") as f:
        json.dump(data, f, indent=2)

    print("Response saved to fantasypros_test.json")

    print()
    print("Top-level keys:")
    print(list(data.keys()))

else:
    print()
    print("FantasyPros returned an error:")
    print(response.text)
