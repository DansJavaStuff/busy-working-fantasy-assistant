import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FANTASYPROS_API_KEY")

url = (
    "https://api.fantasypros.com/public/v2/json/"
    "nfl/2026/consensus-rankings"
)

headers = {
    "x-api-key": API_KEY,
}

tests = [
    {"scoring": "HALF"},
    {"position": "FLX", "scoring": "HALF"},
    {"position": "OP", "scoring": "HALF"},
]

for params in tests:
    print()
    print("Testing:", params)

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    print("Status:", response.status_code)

    if response.ok:
        data = response.json()

        print("Count:", data.get("count"))
        print("Type:", data.get("type"))
        print("Ranking type:", data.get("ranking_type_name"))
        print("Position:", data.get("position_id"))
        print("Limited:", data.get("public_api_limited"))

        for player in data.get("players", [])[:10]:
            print(
                player.get("rank_ecr"),
                player.get("player_name"),
                player.get("player_position_id"),
                player.get("pos_rank"),
            )
    else:
        print(response.text)
