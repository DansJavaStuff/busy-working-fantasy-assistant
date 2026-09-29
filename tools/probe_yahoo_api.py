import json

from yahoo import (
    refresh_access_token,
    yahoo_get,
)


def main():
    print("Refreshing OAuth token...")

    try:
        token = refresh_access_token()
    except Exception as exc:
        print("OAuth: FAILED")
        print(exc)
        return

    print("OAuth: OK")
    print(
        "Token expires in:",
        token.get("expires_in"),
        "seconds",
    )

    print()
    print("Testing Yahoo Fantasy API...")

    response = yahoo_get(
        "users;use_login=1/"
        "games;game_codes=nfl/"
        "leagues"
    )

    print("HTTP:", response.status_code)

    if response.ok:
        print("Fantasy API: AVAILABLE")
        print()
        print(
            json.dumps(
                response.json(),
                indent=2,
            )
        )
        return

    try:
        error = response.json()
    except ValueError:
        error = None

    description = (
        error
        .get("error", {})
        .get("description")
        if error
        else None
    )

    if (
        response.status_code == 401
        and description
        and "additional_authorization_required"
        in description
    ):
        print(
            "Fantasy API: NOT PROVISIONED"
        )
        print(
            "Reason: "
            "additional_authorization_required"
        )
        return

    print("Fantasy API: ERROR")
    print(response.text)


if __name__ == "__main__":
    main()

