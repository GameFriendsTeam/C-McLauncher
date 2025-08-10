import requests
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time

class AuthState:
    """Класс для хранения состояния авторизации между потоками"""
    def __init__(self):
        self.code = None
        self.event = threading.Event()
        self.server = None

def get_account(client_id):
    """
    Gets Minecraft account data via Microsoft OAuth
    """

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
                self.wfile.write(b"<h1>Auth successful! You can close this window.</h1>")
                auth_state.event.set()
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Error: Missing authorization code")
    
    auth_state = AuthState()
    
    server_address = ('localhost', 8080)
    auth_state.server = HTTPServer(server_address, CallbackHandler)
    
    server_thread = threading.Thread(target=auth_state.server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    print("Server started, opening browser for authorization...")
    webbrowser.open(auth_url)
    
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

    return {
        "username": profile_response["name"],
        "uuid": profile_response["id"],
        "access_token": mc_response['access_token']
    }

if __name__ == "__main__":
    CLIENT_ID = "eec03098-1390-4363-b06b-ac8e519fca70"
    
    try:
        print("Starting authorization process...")
        account = get_account(CLIENT_ID)
        print("\nAuthorization successful!")
        print(f"Username: {account['username']}")
        print(f"UUID: {account['uuid']}")
        print(f"Access token: {account['access_token'][:15]}...")
    except Exception as e:
        print(f"\nAuthorization error: {str(e)}")