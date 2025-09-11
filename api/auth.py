import json, requests, os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from api.tools import open_browser
from loguru import logger
import threading
import time

html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Authorization Successful</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }
        h1 {
            color: #4CAF50;
        }
        p {
            color: #555;
        }
    </style>
    <script>
        setTimeout(() => {
            window.close();
        }, 5000);
    </script>
</head>
<body>
    <h1>Auth successful!</h1>
    <p>This page will close in 5 seconds.</p>
    <p>You can also <a onclick="window.close();">close it manually</a>.</p>
</body>
</html>
"""

class AuthState:
    def __init__(self):
        self.code = None
        self.event = threading.Event()
        self.server = None

class AccountManager:
    def __init__(self, storage_file="account_data.json"):
        self.storage_file = storage_file
    
    def load_account_data(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return None
    
    def save_account_data(self, data):
        with open(self.storage_file, 'w') as f:
            json.dump(data, f)
    
    def is_token_valid(self, account_data):
        if not account_data or 'expires_at' not in account_data:
            return False
        
        return time.time() < account_data['expires_at'] - 300

def get_account(client_id):
    manager = AccountManager()
    account_data = manager.load_account_data()
    
    if manager.is_token_valid(account_data):
        return account_data
    
    if account_data and 'refresh_token' in account_data:
        try:
            new_data = refresh_token(client_id, account_data['refresh_token'])
            manager.save_account_data(new_data)
            return new_data
        except Exception as e:
            logger.error(f"Token refresh failed: {e}. Starting new authentication.")
    
    return full_authentication(client_id, manager)

def refresh_token(client_id, refresh_token):
    token_data = {
        "client_id": client_id,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    token_response = requests.post(
        "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
        data=token_data
    ).json()

    if "error" in token_response:
        error_msg = token_response.get('error_description', 'Unknown token error')
        raise Exception(f"Token refresh error: {error_msg}")

    return get_minecraft_data(token_response)

def full_authentication(client_id, manager):
    redirect_uri = "http://localhost:8080"
    auth_url = (
        f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?"
        f"client_id={client_id}&"
        "response_type=code&"
        f"redirect_uri={redirect_uri}&"
        "scope=XboxLive.signin%20offline_access&"
        "prompt=select_account"
    )

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = urlparse(self.path).query
            params = parse_qs(query)
            
            if "code" in params:
                auth_state.code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(html.encode())
                auth_state.event.set()
            else:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Error: Missing authorization code")
    
    auth_state = AuthState()
    
    server_address = ('localhost', 8080)
    auth_state.server = HTTPServer(server_address, CallbackHandler)
    
    server_thread = threading.Thread(target=auth_state.server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    open_browser(auth_url)
    
    if not auth_state.event.wait(timeout=120):
        auth_state.server.shutdown()
        raise Exception("Authorization timeout expired")
    
    auth_state.server.shutdown()
    
    if not auth_state.code:
        raise Exception("Authorization failed: No code received")

    token_data = {
        "client_id": client_id,
        "code": auth_state.code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    token_response = requests.post(
        "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
        data=token_data
    ).json()

    if "error" in token_response:
        error_msg = token_response.get('error_description', 'Unknown token error')
        raise Exception(f"Token error: {error_msg}")

    account_data = get_minecraft_data(token_response)
    manager.save_account_data(account_data)
    
    return account_data

def get_minecraft_data(token_response):
    xbl_payload = {
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": f"d={token_response['access_token']}"
        },
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType": "JWT"
    }
    xbl_response = requests.post(
        "https://user.auth.xboxlive.com/user/authenticate",
        json=xbl_payload,
        headers={"Content-Type": "application/json"}
    ).json()

    xsts_payload = {
        "Properties": {
            "SandboxId": "RETAIL",
            "UserTokens": [xbl_response["Token"]]
        },
        "RelyingParty": "rp://api.minecraftservices.com/",
        "TokenType": "JWT"
    }
    xsts_response = requests.post(
        "https://xsts.auth.xboxlive.com/xsts/authorize",
        json=xsts_payload,
        headers={"Content-Type": "application/json"}
    ).json()
    
    if "Token" not in xsts_response:
        error = xsts_response.get("XErr", "Unknown error")
        raise Exception(f"XSTS authentication failed: {error}")
    
    user_hash = xsts_response["DisplayClaims"]["xui"][0]["uhs"]

    mc_payload = {
        "identityToken": f"XBL3.0 x={user_hash};{xsts_response['Token']}"
    }
    mc_response = requests.post(
        "https://api.minecraftservices.com/authentication/login_with_xbox",
        json=mc_payload
    ).json()
    
    if "access_token" not in mc_response:
        error = mc_response.get("errorMessage", "Minecraft authentication failed")
        raise Exception(error)

    profile_response = requests.get(
        "https://api.minecraftservices.com/minecraft/profile",
        headers={"Authorization": f"Bearer {mc_response['access_token']}"}
    ).json()
    
    if "error" in profile_response:
        error = profile_response.get("errorMessage", "Failed to get profile")
        raise Exception(f"Profile error: {error}")

    expires_at = time.time() + token_response['expires_in']
    
    data = {
        "username": profile_response["name"],
        "uuid": profile_response["id"],
        "access_token": mc_response['access_token'],
        "refresh_token": token_response['refresh_token'],
        "expires_at": expires_at
    }

    return data