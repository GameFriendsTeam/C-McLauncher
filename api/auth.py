import requests
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

def get_account(client_id):
    """
    Получает данные аккаунта Minecraft через Microsoft OAuth
    
    :param client_id: Идентификатор приложения из Azure Portal
    :return: Словарь с данными аккаунта (username, uuid, access_token)
    """
    # 1. Настройки
    redirect_uri = "http://localhost:8080/callback"
    auth_url = (
        f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?"
        f"client_id={client_id}&"
        "response_type=code&"
        f"redirect_uri={redirect_uri}&"
        "scope=XboxLive.signin%20offline_access&"
        "prompt=select_account"
    )

    # 2. Класс для обработки callback
    class CallbackHandler(BaseHTTPRequestHandler):
        code = None
        
        def do_GET(self):
            query = urlparse(self.path).query
            params = parse_qs(query)
            
            if "code" in params:
                self.code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Auth successful! You can close this window.</h1>")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Error: Missing authorization code")
            
            threading.Thread(target=self.server.shutdown, daemon=True).start()
    
    # 3. Запуск HTTP-сервера для перехвата кода
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    # 4. Открытие браузера для авторизации
    webbrowser.open(auth_url)
    
    # Ожидание завершения сервера (получения кода)
    while server_thread.is_alive():
        server_thread.join(1)

    if not CallbackHandler.code:
        raise Exception("Authorization failed: No code received")

    # 5. Получение Microsoft токенов
    token_data = {
        "client_id": client_id,
        "code": CallbackHandler.code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    token_response = requests.post(
        "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
        data=token_data
    ).json()

    if "error" in token_response:
        raise Exception(f"Token error: {token_response['error_description']}")

    # 6. Получение Xbox Live токена
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

    # 7. Получение XSTS токена
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
    user_hash = xsts_response["DisplayClaims"]["xui"][0]["uhs"]

    # 8. Получение Minecraft токена
    mc_payload = {
        "identityToken": f"XBL3.0 x={user_hash};{xsts_response['Token']}"
    }
    mc_response = requests.post(
        "https://api.minecraftservices.com/authentication/login_with_xbox",
        json=mc_payload
    ).json()

    # 9. Получение профиля Minecraft
    profile_response = requests.get(
        "https://api.minecraftservices.com/minecraft/profile",
        headers={"Authorization": f"Bearer {mc_response['access_token']}"}
    ).json()

    return {
        "username": profile_response["name"],
        "uuid": profile_response["id"],
        "access_token": mc_response["access_token"]
    }

# Пример использования
if __name__ == "__main__":
    # Замените на ваш Client ID из Azure
    CLIENT_ID = "YOUR_CLIENT_ID_HERE"
    
    try:
        account = get_account(CLIENT_ID)
        print("Успешная авторизация!")
        print(f"Имя пользователя: {account['username']}")
        print(f"UUID: {account['uuid']}")
        print(f"Токен доступа: {account['access_token'][:15]}...")
    except Exception as e:
        print(f"Ошибка авторизации: {str(e)}")