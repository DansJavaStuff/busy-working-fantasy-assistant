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
    {
        "position": "OP",
        "scoring": "HALF",
        "type": "ADP",
    },
    {
        "position": "OP",
        "scoring": "HALF",
        "ranking_type": "ADP",
    },
    {
        "position": "OP",
        "scoring": "HALF",
        "type": "draft",
    },
]

for params in tests:
    print()
    print("=" * 70)
    print("Testing:", params)

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    print("HTTP:", response.status_code)

    if not response.ok:
        print(response.text)
        continue

    data = response.json()

    print("type:", data.get("type"))
    print("ranking_type_name:", data.get("ranking_type_name"))
    print("count:", data.get("count"))
    print("limit:", data.get("limit"))
    print("limited:", data.get("public_api_limited"))

    for player in data.get("players", [])[:15]:
        print(
            player.get("rank_ecr"),
            player.get("player_name"),
            player.get("player_position_id"),
            player.get("pos_rank"),
        )
