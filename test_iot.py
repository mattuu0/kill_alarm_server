import websocket
import json
import time
import schedule
import threading

timer_tag = "timer_data"

#タイマーを削除する
def clear_timer():
    schedule.clear(timer_tag)

def add_timer(timer_data):
    pass

def test_print():
    print("hello")

device_data = {"deviceToken": "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJkZXZpY2VpZCI6IjI3OTNkODM2M2UwOTFjMjRjNGE3MGQwMWI4YzY0YzgwMTBhMDk5MzlkNjNiMGZiYjcxY2RjYWJjNDI2NjA3NTI5ODVlM2FhN2E2NmM4ZjBlMzFhYzIyNDMzNzNkNTZjMTEwNjlmY2M5MTRiNTNkN2ZkYmE3NTM5ZmYxNmZjNTQ4IiwidG9rZW5pZCI6ImJmYjgyZTgyLThmODEtNDEzZi05ZWQxLWE5ZjFhYzU1NDBkOCJ9.cV4I6nv7ZNfy69knf9_VEcxjfLtB_QFeGo8tEPhvw928NeunxcLdA3m81kS57qkqyHnpA9Oz1eICXVsA1AvN_w", "deviceid": "2793d8363e091c24c4a70d01b8c64c8010a09939d63b0fbb71cdcabc42660752985e3aa7a66c8f0e31ac2243373d56c11069fcc914b53d7fdba7539ff16fc548"}

def on_message(wsapp, message):
    global loop_connect

    print(message)
    load_dict = json.loads(message)

    match load_dict["msgcode"]:
        case "11110":
            loop_connect = False
        case "11142":
            pass

def on_open(wsapp):
    print("Connected")
    auth_data = {
        "msgtype": 'authToken',
        "token" : device_data["deviceToken"]
    }

    wsapp.send(json.dumps(auth_data))
loop_connect = True

def connect_server():
    global loop_connect
    while loop_connect:
        wsapp = websocket.WebSocketApp("ws://127.0.0.1:8000/iotws", on_message=on_message,on_open=on_open)

        wsapp.run_forever()
        
        wsapp.close()

        if not loop_connect:
            break

        print("reconnect")

        time.sleep(3)

if __name__ == "__main__":
    server_thread = threading.Thread(target=connect_server)

    server_thread.start()
    while True:
        schedule.run_pending()
        time.sleep(30)