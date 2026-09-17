import json
from collections import deque

import requests

from fantasypros import API_KEY, record_api_call


BASE_URL = "https://api.fantasypros.com/public/v2/json/nfl/players"


def describe(value):
    if isinstance(value, dict):
        return f"dict({len(value)})"
    if isinstance(value, list):
        return f"list({len(value)})"
    return type(value).__name__


def playerish_records(payload, limit=8):
    queue = deque([("$", payload)])
    found = []

    while queue and len(found) < limit:
        path, value = queue.popleft()

        if isinstance(value, dict):
            lowered = {str(key).lower() for key in value}
            has_name = any(
                key in lowered
                for key in {
                    "name",
                    "player_name",
                    "fullname",
                    "full_name",
                }
            )
            has_id = any(
                key in lowered
                for key in {
                    "id",
                    "player_id",
                    "fantasypros_id",
                }
            )

            if has_name or has_id:
                safe = {}
                for key, item in value.items():
                    key_text = str(key)
                    key_lower = key_text.lower()

                    if any(
                        token in key_lower
                        for token in {
                            "key",
                            "token",
                            "secret",
                            "image",
                            "photo",
                        }
                    ):
                        continue

                    if isinstance(item, (str, int, float, bool)) or item is None:
                        safe[key_text] = item
                    elif isinstance(item, (dict, list)):
                        safe[key_text] = describe(item)

                found.append((path, safe))

            for key, item in value.items():
                if isinstance(item, (dict, list)):
                    queue.append((f"{path}.{key}", item))

        elif isinstance(value, list):
            for index, item in enumerate(value[:100]):
                if isinstance(item, (dict, list)):
                    queue.append((f"{path}[{index}]", item))

    return found


def main():
    if not API_KEY:
        raise SystemExit("FANTASYPROS_API_KEY missing from .env")

    response = requests.get(
        BASE_URL,
        headers={"x-api-key": API_KEY},
        timeout=30,
    )
    record_api_call(response)

    print(f"HTTP {response.status_code}")
    response.raise_for_status()

    payload = response.json()

    print(f"Top level: {describe(payload)}")

    if isinstance(payload, dict):
        print("Top-level keys:")
        for key, value in payload.items():
            print(f"  {key}: {describe(value)}")

    print()
    print("Player-like records found:")

    records = playerish_records(payload)

    if not records:
        print("  None found in the first searchable portion of the response.")
    else:
        for path, record in records:
            print(f"\n{path}")
            print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
