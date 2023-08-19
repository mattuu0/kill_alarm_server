import requests
import json
import websocket

host = "127.0.0.1:8000"
base_url = f"http://{host}"

headersList = {
    "Accept": "*/*",
    "User-Agent": "Thunder Client (https://www.thunderclient.com)",
    "Content-Type": "application/json" 
}

payload = json.dumps({
    "username": "test1",
    "password": "password"
})

#ログインする
response = requests.request("POST", f"{base_url}/login", data=payload,  headers=headersList)

#成功したら
print(response.status_code)

if int(response.status_code) == 200:
    res_json = response.json()

    #リフレッシュトークン
    refreh_token = res_json["refresh_token"]

    #アクセストークン
    access_token = res_json["access_token"]

    auth_header = {
        "Accept": "*/*",
        "Authorization": f"Bearer {access_token}" 
    }


    res = requests.get(f"{base_url}/ws_token",headers=auth_header)
    ws_token = res.json()["token"]

    websocket.enableTrace(False)

    ws = websocket.WebSocket()
    ws.connect(f"ws://{host}/ws")

    ws_auth = {
        "msgtype" : "authToken",
        "token" : access_token
    }

    ws.send(json.dumps(ws_auth))
    print(ws.recv())
    
    payload = {
        "msgtype" : "friend_request",
        "userid" : ""
    }


response.close()
