import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
TOKEN_FILE = BASE_DIR / "yahoo_token.json"

TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
FANTASY_BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"

load_dotenv(dotenv_path=ENV_FILE)


def load_token():
    if not TOKEN_FILE.exists():
        raise RuntimeError(
            "Yahoo token file not found. "
            "Complete the Yahoo OAuth login first."
        )

    return json.loads(TOKEN_FILE.read_text())


def save_token(token):
    TOKEN_FILE.write_text(
        json.dumps(token, indent=2)
    )


def refresh_access_token():
    """
    Use the stored Yahoo refresh token to obtain a new
    access token.

    Yahoo may or may not return a replacement refresh token,
    so preserve the existing one if necessary.
    """

    client_id = os.environ["YAHOO_CLIENT_ID"]
    client_secret = os.environ["YAHOO_CLIENT_SECRET"]
    redirect_uri = os.environ["YAHOO_REDIRECT_URI"]

    old_token = load_token()

    refresh_token = old_token.get("refresh_token")

    if not refresh_token:
        raise RuntimeError(
            "Yahoo refresh token is missing. "
            "OAuth authorisation must be completed again."
        )

    response = requests.post(
        TOKEN_URL,
        auth=(client_id, client_secret),
        data={
            "grant_type": "refresh_token",
            "redirect_uri": redirect_uri,
            "refresh_token": refresh_token,
        },
        timeout=30,
    )

    response.raise_for_status()

    new_token = response.json()

    # Yahoo does not necessarily return a new refresh token
    # every time.
    if not new_token.get("refresh_token"):
        new_token["refresh_token"] = refresh_token

    expires_in = int(
        new_token.get("expires_in", 3600)
    )

    # Refresh one minute before Yahoo considers the token
    # expired.
    new_token["expires_at"] = (
        int(time.time())
        + expires_in
        - 60
    )

    save_token(new_token)

    return new_token


def get_valid_token():
    """
    Return a usable Yahoo OAuth token.

    Older token files do not contain expires_at, so the first
    request after installing this code will refresh once and
    upgrade the saved token automatically.
    """

    token = load_token()

    expires_at = token.get("expires_at")

    if not expires_at:
        return refresh_access_token()

    if time.time() >= expires_at:
        return refresh_access_token()

    return token


def yahoo_get(path, params=None):
    """
    Perform an authenticated Yahoo Fantasy GET request.

    If Yahoo reports that the access token expired unexpectedly,
    refresh the token and retry once.
    """

    if path.startswith("http"):
        url = path
    else:
        url = (
            f"{FANTASY_BASE_URL}/"
            f"{path.lstrip('/')}"
        )

    token = get_valid_token()

    headers = {
        "Authorization": (
            f"Bearer {token['access_token']}"
        )
    }

    request_params = {
        "format": "json",
    }

    if params:
        request_params.update(params)

    response = requests.get(
        url,
        headers=headers,
        params=request_params,
        timeout=30,
    )

    # Token timestamps can occasionally get out of sync.
    # Only retry when Yahoo explicitly says the token expired.
    if (
        response.status_code == 401
        and "token_expired" in response.text
    ):
        token = refresh_access_token()

        headers["Authorization"] = (
            f"Bearer {token['access_token']}"
        )

        response = requests.get(
            url,
            headers=headers,
            params=request_params,
            timeout=30,
        )

    return response
