import json

from yahoo import yahoo_get


response = yahoo_get(
    "users;use_login=1/"
    "games;game_codes=nfl/"
    "leagues"
)

print("HTTP status:", response.status_code)

if response.ok:
    print()
    print("SUCCESS!")
    print()

    data = response.json()
    print(json.dumps(data, indent=2))

else:
    print()
    print("Yahoo returned an error:")
    print()
    print(response.text)
