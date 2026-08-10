import os
import secrets
import json
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, redirect, request, session

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

CLIENT_ID = os.getenv("YAHOO_CLIENT_ID")
CLIENT_SECRET = os.getenv("YAHOO_CLIENT_SECRET")
REDIRECT_URI = os.getenv("YAHOO_REDIRECT_URI")

AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"

TOKEN_FILE = Path("yahoo_token.json")


@app.route("/")
def home():
    return """
    <html>
        <head>
            <title>Busy Working Fantasy Assistant</title>
        </head>
        <body>
            <h1>🏈 Busy Working Fantasy Assistant</h1>
            <p>Yahoo Fantasy connection test.</p>

            <p>
                <a href="/login">
                    Connect to Yahoo
                </a>
            </p>
        </body>
    </html>
    """


@app.route("/login")
def login():
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": state,
    }

    req = requests.Request(
        "GET",
        AUTH_URL,
        params=params
    ).prepare()

    return redirect(req.url)


@app.route("/oauth/callback")
def oauth_callback():

    error = request.args.get("error")

    if error:
        return f"Yahoo returned an error: {error}", 400

    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        return "No authorization code returned by Yahoo.", 400

    if state != session.get("oauth_state"):
        return "OAuth state mismatch.", 400

    token_response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": code,
        },
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=30,
    )

    if not token_response.ok:
        return (
            "<h1>Token exchange failed</h1>"
            f"<p>Status: {token_response.status_code}</p>"
            f"<pre>{token_response.text}</pre>",
            500,
        )

    token_data = token_response.json()

    # Store Yahoo tokens locally on the Pi.
    TOKEN_FILE.write_text(
        json.dumps(token_data, indent=2)
    )

    # Only the Pi user can read/write the token file.
    TOKEN_FILE.chmod(0o600)

    session["yahoo_connected"] = True

    return """
    <html>
        <head>
            <title>Yahoo Connected</title>
        </head>
        <body>
            <h1>✅ Connected to Yahoo!</h1>
            <p>The OAuth authorization worked.</p>
            <p>Yahoo tokens have been stored securely.</p>
            <p>Next step: access your Fantasy Football league.</p>
        </body>
    </html>
    """


if __name__ == "__main__":

    if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
        raise RuntimeError(
            "Yahoo OAuth settings are missing from .env"
        )

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )
