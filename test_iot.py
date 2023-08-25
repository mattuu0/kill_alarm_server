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

device_data = {"deviceToken": "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJkZXZpY2VpZCI6ImI4ZjlkNjcwYzkyYWJlMTFlYjAyNTZlOGI2ZWRhYTE3OGRkMmRmNGI1NDdlNWFmMjgwOTU5YWMzYjU0NDUzMzg3OGNhZGZmOGYxZWU1NDEzNmEzMDgzOTMzN2E5YmY3YTNiZWNiYjNhOWJhNjEwOTYxOGQ0MWMzMjM0OTk1MTY5IiwidG9rZW5pZCI6ImIzZTVhYTY0LWMxYmEtNGI5Ni04NzA0LTY5MTgyMGNiYmFlYyJ9.Ten8Aeyy4ZAObRP7rCcQsqt6cCymAGsE-iM7H3qjIKrHyc5v6NKDqFkOVoDaLRrQ02xSIjXnij7YH70b4HDCWw", "deviceid": "b8f9d670c92abe11eb0256e8b6edaa178dd2df4b547e5af280959ac3b544533878cadff8f1ee54136a30839337a9bf7a3becbb3a9ba6109618d41c3234995169"}

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