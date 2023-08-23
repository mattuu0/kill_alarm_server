import os
from dotenv import load_dotenv
# .envファイルの内容を読み込見込む
load_dotenv()


from fastapi import FastAPI,Depends,HTTPException,Security,Request,UploadFile,File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi_jwt import JwtAuthorizationCredentials, JwtAccessBearer,JwtRefreshBearer
from starlette.middleware.cors import CORSMiddleware # 追加
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from PIL import Image
from shutil import copyfile
from typing import List

import jwt
import uvicorn,time
from server_auth.database import (User,
                                  auth_login,
                                  check_registerd_from_userid,
                                  session,
                                  get_user,
                                  create_user,
                                  check_registerd_from_username,
                                  delete_user)
from friends.friend import (delete_friend,
                            create_friend,
                            delete_user as friend_delete_func,
                            get_friends,
                            check_friend,
                            get_info)
from friends.friend_request import (reject_request,
                                    accept_request,
                                    cancel_request,
                                    delete_user as friend_request_delete_func,
                                    create_request,
                                    check_request)
from Iot.iot import (
    pair_device,
    unpair_device,
    get_device_from_userid,
    get_device,
    delete_user as iot_delete_user_func
)
from Iot.auth import (
    algorithm as Iot_Token_Algorithm,
    secret_key as Iot_Token_Secret
)

import datetime,uuid,json

from passlib.context import CryptContext
from starlette.websockets import WebSocket

#Websocket接続中クライアント
websocket_clients = {}

#JWT関連
websocket_security = JwtAccessBearer(secret_key=os.environ["Websocket_Token_Secret"], auto_error=True)
access_security = JwtAccessBearer(secret_key=os.environ["Access_Token_Secret"], auto_error=True)
refresh_security = JwtRefreshBearer(secret_key=os.environ["Refresh_Token_Secret"], auto_error=True)

websocket_token_effective_date = datetime.timedelta(minutes=5)           #Websocket Token 有効期限     5分
access_token_effective_date = datetime.timedelta(minutes=60)           #Access Token 有効期限     60分
refresh_token_effective_date = datetime.timedelta(days=90)      #Refresh Token 有効期限 90日

#ここまで
limiter = Limiter(key_func=get_remote_address)
#サーバ
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,   # 追記により追加
    allow_methods=["*"],      # 追記により追加
    allow_headers=["*"]       # 追記により追加
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

#設定
user_datas_dir = os.path.abspath("./UserDatas")
base_icon = os.path.join(user_datas_dir,"default_icon.png")
payloads_data = ["light","water","vibration","blow","sound"]
strength_data = ["high","middle","low"]

#フォルダ初期化
try:
    os.makedirs(user_datas_dir)
except:
    import traceback
    traceback.print_exc()

#トークン関係
pwd_cxt = CryptContext(schemes=['bcrypt'], deprecated='auto')
class token_util():
    #リフレッシュトークン生成
    def generate_refresh_token(userid : str):
        tokenid = str(uuid.uuid4())

        #Token
        subjects = {
            "userid" : userid,
            "tokenid" : tokenid
        }

        #リフレッシュトークン
        refresh_token = refresh_security.create_refresh_token(subject = subjects,expires_delta = refresh_token_effective_date)

        return tokenid,refresh_token
    
    #アクセストークン生成
    def generate_access_token(userid : str,refresh_tokenid : str):
        is_registerd,user = check_registerd_from_userid(userid)

        tokenid = str(uuid.uuid4())
        #ユーザーが登録されているか
        if is_registerd:
            
            #トークンのIDが一致するか
            if token_util.verify_refresh_token(userid,refresh_tokenid):
                subjects = {
                    "userid" : userid,
                    "tokenid" : tokenid
                }

                #アクセストークン
                access_token = access_security.create_access_token(subject = subjects,expires_delta = access_token_effective_date)
                user.access_tokenid = tokenid
                session.commit()

                return True,access_token,tokenid
            else:
                return False,"",""
        
        return False,"",""
    
    #Websocket用トークン生成
    def generate_websocket_token(userid : str,access_tokenid : str):
        is_registerd,user = check_registerd_from_userid(userid)

        tokenid = str(uuid.uuid4())
        #ユーザーが登録されているか
        if is_registerd:
            
            #トークンのIDが一致するか
            if token_util.verify_access_token(userid,access_tokenid):
                subjects = {
                    "userid" : userid,
                    "tokenid" : tokenid
                }

                #Websocketトークン
                websocket_token = websocket_security.create_access_token(subject = subjects,expires_delta = websocket_token_effective_date)
                user.websocket_tokenid = tokenid
                session.commit()

                return True,websocket_token,tokenid
            else:
                return False,"",""
        
        return False,"",""

    #リフレッシュトークン検証
    def verify_refresh_token(userid : str,refesh_tokenid : str):
        #ユーザーが登録されているか
        is_registerd,user = check_registerd_from_userid(userid)

        if not is_registerd:
            return False

        #トークンのIDが一致するか
        return str(user.refresh_tokenid) == refesh_tokenid
    
    #アクセストークン検証
    def verify_access_token(userid : str,access_tokenid : str):
        #ユーザーが登録されているか
        is_registerd,user = check_registerd_from_userid(userid)

        if not is_registerd:
            return False

        #トークンのIDが一致するか
        return str(user.access_tokenid) == access_tokenid
    
    #Websocket認証
    def verify_websocket_token(token : str):
        try:
            decode_dict = dict(websocket_security._decode(token))

            userid = str(decode_dict["subject"]["userid"])
            tokenid = str(decode_dict["subject"]["tokenid"])
            exp_time = int(decode_dict["exp"])

            now_time = int(time.time())

            #有効期限より現在時刻のほうが大きい場合
            if now_time > exp_time:
                return False
            
            is_registerd,user = check_registerd_from_userid(userid)

            if not is_registerd:
                return False

            #トークンのIDが一致するか
            return str(user.websocket_tokenid) == tokenid
        except:
            import traceback
            traceback.print_exc()

            return False
#ここまで

class UserAuth(BaseModel):
    username: str
    password: str
#認証関係の処理

#ログイン
@app.post("/login")
@limiter.limit("10/5seconds")
def login(request: Request,auth_data : UserAuth):
    # raise HTTPException(404, detail="Not Found")
    #登録されているか確認
    is_registerd,user = check_registerd_from_username(auth_data.username)

    #登録されていなかったら
    if not is_registerd:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    is_success,user = auth_login(auth_data.username,auth_data.password)    #ログインする

    #成功したら
    if is_success:
        userid = str(user.userid)

        #リフレッシュトークン生成
        refresh_tokenid,refresh_token = token_util.generate_refresh_token(userid)   
        
        #リフレッシュトークン更新
        user.refresh_tokenid = refresh_tokenid
        session.commit()

        #アクセストークン生成
        is_success,access_token,access_tokenid = token_util.generate_access_token(userid,refresh_tokenid)

        if is_success:
            return {"refresh_token" : refresh_token,"access_token" : access_token}
    else:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    raise HTTPException(status_code=401, detail="Error")

#ログイン
@app.post("/logout")
async def logout(request: Request,credentials: JwtAuthorizationCredentials = Security(refresh_security),):
    subjects = dict(credentials.subject)
    userid = subjects["userid"]                                     #ユーザーID取得
    access_tokenid = subjects["tokenid"]                            #アクセストークンID
    
    #アクセストークン検証
    if token_util.verify_refresh_token(userid,access_tokenid):
        #ユーザーを取得する
        user:User = get_user(userid)

        #登録されているか
        if user:
            #すべてのトークンを無効にする
            user.access_tokenid = ""
            user.refresh_tokenid = ""
            user.websocket_tokenid = ""

            #接続を閉じる
            await close_client(userid)

            session.commit()

            return {"status":"success"}
    
#サインイン
@app.post("/signup")
@limiter.limit("10/5seconds")
def signup(request: Request,singin_data : UserAuth):
    is_registerd,user = check_registerd_from_username(singin_data.username)

    #既にユーザー名で登録されていたら
    if is_registerd:
        raise HTTPException(status_code=401, detail="User already exists")
    
    user = create_user(singin_data.username,singin_data.password)    #ユーザーを作成する
    
    #成功したら
    userid = str(user.userid)

    #リフレッシュトークン生成
    refresh_tokenid,refresh_token = token_util.generate_refresh_token(userid)   
        
    #リフレッシュトークン更新
    user.refresh_tokenid = refresh_tokenid
    session.commit()

    #アクセストークン生成
    is_success,access_token,access_tokenid = token_util.generate_access_token(userid,refresh_tokenid)

    if is_success:
        icon_filepath = os.path.join(user_datas_dir,f"{userid}.png")                 #アイコンのパス
        timer_filepath = os.path.join(user_datas_dir,f"{userid}.json")               #タイマー情報のパス

        if os.path.commonprefix((os.path.realpath(icon_filepath),user_datas_dir)) != user_datas_dir:      #パス検証
            raise HTTPException(status_code=401, detail="Invalid Path")

        if os.path.commonprefix((os.path.realpath(timer_filepath),user_datas_dir)) != user_datas_dir:      #パス検証
            raise HTTPException(status_code=401, detail="Invalid Path")

        #ファイルが存在するか
        if not os.path.exists(icon_filepath):
            copyfile(base_icon,icon_filepath)

        if not os.path.exists(timer_filepath):
            with open(timer_filepath,"w") as create_file:      #空のファイルを生成する
                json.dump({},create_file)
        return {"refresh_token" : refresh_token,"access_token" : access_token}

    raise HTTPException(status_code=401, detail="Error")

#アカウント削除
@app.delete("/delete_user")
@limiter.limit("10/5seconds")
async def deleteUser(request: Request,credentials: JwtAuthorizationCredentials = Security(refresh_security),):
    subjects = dict(credentials.subject)
    userid = subjects["userid"]                                     #ユーザーID取得
    access_tokenid = subjects["tokenid"]                            #アクセストークンID
    
    #アクセストークン検証
    if token_util.verify_refresh_token(userid,access_tokenid):
        #削除処理
        friend_delete_func(userid)
        friend_request_delete_func(userid)
        iot_delete_user_func(userid)
        delete_user(userid)
        
        #アイコンファイルパス
        icon_filepath = os.path.join(user_datas_dir,f"{userid}.png")

        #辞書ファイルパス
        timer_filepath = os.path.join(user_datas_dir,f"{userid}.json")

        #アイコンを削除する
        if os.path.commonprefix((os.path.realpath(icon_filepath),user_datas_dir)) == user_datas_dir:
            if os.path.exists(icon_filepath):
                os.remove(icon_filepath)

        #タイマーデータを削除する
        if os.path.commonprefix((os.path.realpath(timer_filepath),user_datas_dir)) == user_datas_dir:
            if os.path.exists(timer_filepath):
                os.remove(timer_filepath)

        #Websocketを切断する
        await close_client(userid)

        return {"status":"success"}
    else:
        raise HTTPException(status_code=401, detail="invalid token")

#アクセストークンを更新する
@app.get('/refresh_token')
@limiter.limit("10/5seconds")
def refresh_token(request: Request,credentials: JwtAuthorizationCredentials = Security(refresh_security),):
    subjects = dict(credentials.subject)

    userid = subjects["userid"]                                                         #ユーザーID取得                     

    #ユーザー取得
    user = get_user(userid)
    if user:
        is_success,token,access_tokenid = token_util.generate_access_token(userid,subjects["tokenid"])     #アクセストークンを生成する

        #成功したら
        if is_success:
            return {"accesstoken" : token}

    raise HTTPException(status_code=401, detail="Invalid refresh token")

#ここまで
class profile_data(BaseModel):
    display_name : str

#プロフィーユ変更
@app.post("/change_profile")
def change_profile(profile : profile_data,credentials: JwtAuthorizationCredentials = Security(access_security)):
    #ディスプレイの長さを検証する
    if str(profile.display_name) > 255:
        raise HTTPException(status_code=400,detail="Display name is too long")
    
    subjects = dict(credentials.subject)
    userid = subjects["userid"]                                     #ユーザーID取得
    access_tokenid = subjects["tokenid"]                            #アクセストークンID
    
    #アクセストークン検証
    if token_util.verify_access_token(userid,access_tokenid): 
        #ユーザーが登録されているか
        is_registerd,user_obj = check_registerd_from_userid(userid)

        #登録されていたら
        if is_registerd:
            #ディスプレイネームを換える
            user_obj.display_name = profile.display_name
            session.commit()
            
            return {"status":"success"}

    raise HTTPException(status_code=401, detail="Invalid Token")
    
#認証が必要なエンドポイント
@app.get('/get_profile')
@limiter.limit("10/5seconds")
def get_userid(request: Request,credentials: JwtAuthorizationCredentials = Security(access_security),):
    subjects = dict(credentials.subject)
    userid = subjects["userid"]                                     #ユーザーID取得
    access_tokenid = subjects["tokenid"]                            #アクセストークンID
    
    #アクセストークン検証
    if token_util.verify_access_token(userid,access_tokenid):
        user_data : User = get_user(userid)

        return {
            "userid" : userid,
            "username" : user_data.username,
            "display_name" : user_data.display_name
        }
    
    raise HTTPException(status_code=401, detail="Invalid Token")

#認証が必要なエンドポイント
@app.get('/ws_token')
@limiter.limit("10/5seconds")
def get_userid(request: Request,credentials: JwtAuthorizationCredentials = Security(access_security),):
    subjects = dict(credentials.subject)
    userid = subjects["userid"]                                     #ユーザーID取得
    access_tokenid = subjects["tokenid"]                            #アクセストークンID
    
    #アクセストークン検証
    if token_util.verify_access_token(userid,access_tokenid):   
        #websocket認証用トークン生成
        is_success,websocket_token,tokenid = token_util.generate_websocket_token(userid,access_tokenid)
    
        #成功したら返す
        if is_success:
            return {"token":websocket_token}
        else:
            raise HTTPException(status_code=500, detail="Failed to generate token")
        
    else:
        raise HTTPException(status_code=401, detail="Invalid Token")

#画像ファイルの最大サイズ   (5MB)
Image_Max_Size = 5 * 1024 * 1024

@app.post('/change_icon')
@limiter.limit("10/5seconds")
def get_userid(request: Request,credentials: JwtAuthorizationCredentials = Security(access_security),file:UploadFile = File(...)):
    subjects = dict(credentials.subject)
    userid = subjects["userid"]                                     #ユーザーID取得
    access_tokenid = subjects["tokenid"]                            #アクセストークンID
    
    #アクセストークン検証
    if token_util.verify_access_token(userid,access_tokenid):
        if file:
            file.file.seek(0,2)
            img_size = file.file.tell()

            #サイズを検証する
            if img_size > Image_Max_Size:
                raise HTTPException(status_code=413, detail="Image file size too large")

            #画像を読み込む
            filepath = os.path.join(user_datas_dir,f"{userid}.png")

            if os.path.commonprefix((os.path.realpath(filepath),user_datas_dir)) != user_datas_dir:
                raise HTTPException(status_code=401, detail="Invalid Path")

            readImg = Image.open(file.file)
            save_img = readImg.convert("RGB")
            save_img.save(filepath)

            return {"status":"success"}
    else:
        raise HTTPException(status_code=401, detail="Invalid Token")


#IOTデバイス
class IotDevice(BaseModel):
    deviceid : str

#デバイスを登録する
@app.post("/pair_iot")
async def pair_iot(request: Request,deviceData : IotDevice,credentials: JwtAuthorizationCredentials = Security(access_security)):
    subjects = dict(credentials.subject)
    userid = subjects["userid"]                                     #ユーザーID取得
    access_tokenid = subjects["tokenid"]                            #アクセストークンID

    return_result = {"msgtype" : "","message" : "","msgcode" : ""}
    #アクセストークン検証
    if token_util.verify_access_token(userid,access_tokenid):
        #ユーザーが既に登録しているか
        already_paierd,device = get_device_from_userid(userid)

        if already_paierd:
            return_result["msgcode"] = "11133"
            return_result["message"] = "You have already paired device"
            return_result["msgtype"] = "Error_Message"
            return return_result

        #登録する
        is_success,device = pair_device(str(deviceData.deviceid),userid)

        #成功したらデバイスIDを返す
        if is_success:
            return_result["msgcode"] = "11134"
            return_result["message"] = "Device registration successful"
            return_result["msgtype"] = "Success_Message"
            return_result["deviceid"] = device.deviceid
            return return_result
        else:
            return_result["msgcode"] = "11135"
            return_result["message"] = "Device registration failure"
            return_result["msgtype"] = "Error_Message"

            return return_result
    else:
        raise HTTPException(status_code=401, detail="invalid token")

#デバイス登録解除
@app.post("/unpair_iot")
async def unpair_iot(request: Request,credentials: JwtAuthorizationCredentials = Security(access_security)):
    subjects = dict(credentials.subject)
    userid = subjects["userid"]                                     #ユーザーID取得
    access_tokenid = subjects["tokenid"]                            #アクセストークンID

    return_result = {"msgtype" : "","message" : "","msgcode" : ""}
    #アクセストークン検証
    if token_util.verify_access_token(userid,access_tokenid):
        #ユーザーが既に登録しているか
        already_paierd,device = get_device_from_userid(userid)

        #登録していなかったら戻る
        if not already_paierd:
            return_result["msgcode"] = "11138"
            return_result["message"] = "No device paired"
            return_result["msgtype"] = "Error_Message"
            return return_result

        #登録解除する
        is_success,device = unpair_device(userid)

        #成功したらデバイスIDを返す
        if is_success:
            return_result["msgcode"] = "11136"
            return_result["message"] = "success to unpair device"
            return_result["msgtype"] = "Success_Message"
            return_result["deviceid"] = device.deviceid
            return return_result
        else:
            return_result["msgcode"] = "11137"
            return_result["message"] = "failed to unpair device"
            return_result["msgtype"] = "Error_Message"

            return return_result
    else:
        raise HTTPException(status_code=401, detail="invalid token")

#タイマーデータを更新する
@app.get("/get_timer")
async def wakeup_friend(request: Request,credentials: JwtAuthorizationCredentials = Security(access_security)):
    subjects = dict(credentials.subject)
    userid = subjects["userid"]                                     #ユーザーID取得
    access_tokenid = subjects["tokenid"]                            #アクセストークンID

    return_result = {"msgtype" : "","message" : "","msgcode" : ""}
    #アクセストークン検証
    if token_util.verify_access_token(userid,access_tokenid):

        timer_filepath = os.path.join(user_datas_dir,f"{userid}.json")

        if os.path.commonprefix((os.path.realpath(timer_filepath),user_datas_dir)) != user_datas_dir:      #パス検証
            raise HTTPException(status_code=401, detail="Invalid Path")
        
        #ファイルを読み込む

        return_dict = {}
        with open(timer_filepath,"r",encoding="utf-8") as read_data:
            return_dict = json.load(read_data)
        
        return_result["msgcode"] = "11145"
        return_result["timer_data"] = return_dict

        return return_result
    else:
        raise HTTPException(status_code=401,detail="Invalid Token")
#タイマー動作
class timer_payload(BaseModel):
    name : str
    strength : str
    args : List[str]

#タイマーデータ
class timers_data(BaseModel):
    call_hour:str                           #起動時間
    call_min:str                            #起動分   
    payloads : List[timer_payload]          #動作一覧
    enabled : bool                          #有効か

class timer_body(BaseModel):
    timers : List[timers_data]

#タイマーデータを更新する
@app.post("/update_timer")
async def wakeup_friend(request: Request,timers_data : timer_body,credentials: JwtAuthorizationCredentials = Security(access_security)):
    subjects = dict(credentials.subject)
    userid = subjects["userid"]                                     #ユーザーID取得
    access_tokenid = subjects["tokenid"]                            #アクセストークンID

    return_result = {"msgtype" : "","message" : "","msgcode" : ""}
    #アクセストークン検証
    if token_util.verify_access_token(userid,access_tokenid):

        timer_filepath = os.path.join(user_datas_dir,f"{userid}.json")

        if os.path.commonprefix((os.path.realpath(timer_filepath),user_datas_dir)) != user_datas_dir:      #パス検証
            raise HTTPException(status_code=401, detail="Invalid Path")

        #フレンドがIOTデバイスを登録しているか
        is_registerd,iot_device = get_device_from_userid(str(userid))

        #登録されていなかったら
        if not is_registerd:
            raise HTTPException(status_code=400, detail="User has not paired any device")

        notify_data = {
            "msgcode" : "11142",
            "timers" : []
        }
        #タイマーを回す
        for timer in timers_data.timers:
            #起こす方法が正しいかを検証する
            payloads = []
            for payload_info in timer.payloads:
                #ペイロードが含まれているか
                if str(payload_info.name).lower() in payloads_data:
                    #強さが含まれているか
                    if str(payload_info.strength).lower() in strength_data:

                        #追加情報
                        add_dict = {
                            "payload_name" : payload_info.name.lower(),
                            "strong" : payload_info.strength.lower(),
                            "args" : payload_info.args
                        }
                    else:
                        #強さが向こうの時
                        raise HTTPException(status_code=400, detail="Invalid Strength")
                    payloads.append(add_dict)
                else:
                    #正しくなければエラー

                    raise HTTPException(status_code=400, detail="Invalid payload")
                
            #タイマー出たを更新する
            with open(timer_filepath,"w",encoding="utf-8") as write_data:
                dump_string = timers_data.model_dump_json(indent=3)
                write_data.write(dump_string)

            #タイマーデータ
            timer_json = {
                "enabled" : timer.enabled,          #有効か
                "call_hour" : timer.call_hour,      #起動時間
                "call_min" : timer.call_min,        #起動分
                "payloads" : payloads               #動作内容
            }            

            #タイマー追加
            notify_data["timers"].append(timer_json)

        await send_msg(iot_device.deviceid,notify_data)

        return_result["msgcode"] = "11140"
        return_result["msgtype"] = "server_msg"
        return_result["message"] = "success"
        return return_result
    
    raise HTTPException(status_code=400,detail="Bad Timer")

#起こす内容
class payload_data(BaseModel):
    payload_name : str

#起こした人の情報
class wakeup_payload(BaseModel):
    friendid:str
    payloads:List[payload_data]

#友人を起こす
@app.post("/wakeup")
async def wakeup_friend(request: Request,select_data : wakeup_payload,credentials: JwtAuthorizationCredentials = Security(access_security)):
    subjects = dict(credentials.subject)
    userid = subjects["userid"]                                     #ユーザーID取得
    access_tokenid = subjects["tokenid"]                            #アクセストークンID

    return_result = {"msgtype" : "","message" : "","msgcode" : ""}
    #アクセストークン検証
    if token_util.verify_access_token(userid,access_tokenid):
        #フレンドが登録されているか
        is_registerd,user = check_registerd_from_userid(select_data.friendid)

        if not is_registerd:
            raise HTTPException(status_code=404, detail="no friends found")

        #フレンドかどうか確認する
        is_friend,friend = check_friend(userid,select_data.friendid)

        #フレンドじゃなければ戻る
        if not is_friend:
            raise HTTPException(status_code=403, detail="not friends")

            
        #フレンドがIOTデバイスを登録しているか
        is_registerd,iot_device = get_device_from_userid(str(select_data.friendid))

        #登録されていなかったら
        if not is_registerd:
            raise HTTPException(status_code=400, detail="User has not paired any device")
        
        #起こす方法が正しいかを検証する
        payloads = []
        for payload_info in select_data.payloads:
            #ペイロードが含まれているか
            if str(payload_info.payload_name).lower() in payloads_data:
                add_dict = {
                    "payload_name" : payload_info.payload_name
                }

                payloads.append(add_dict)
            else:
                #正しくなければエラー
                raise HTTPException(status_code=400, detail="Invalid payload")

        #通知データ
        notify_payload = {
            "msgcode" : "11143",
            "call_user" : str(userid),
            "payloads" : payloads
        }

        #IOTへ通知する
        await send_msg(iot_device.deviceid,notify_payload)
        return {"status":"success"}
    else:
        raise HTTPException(status_code=403, detail="Invalid Token")

#ユーザーIDを取得する
@app.get("/getId/{username}")
def get_userid_from_name(username : str):
    #ユーザーが登録されているか確認
    is_registred,user = check_registerd_from_username(username)

    if is_registred:
        return {"userid":str(user.userid)}
    
    raise HTTPException(status_code=404,detail="User Not Found")

#ユーザーアイコンを取得する
@app.get("/geticon/{userid:path}")
async def get_icon(userid : str):
    filepath = os.path.join(user_datas_dir,f"{userid}.png")

    if os.path.commonprefix((os.path.realpath(filepath),user_datas_dir)) != user_datas_dir:
        raise HTTPException(status_code=401, detail="Invalid Path")

    #ファイルが存在するか
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File Not Found")

    #ファイルを返す
    response = FileResponse(
        path=filepath,
        filename=f"{userid}.png"
    )

    return response
#フレンド関係
async def send_friend_request(userid : str,friend_userid : str):
    return_result = {"msgtype" : "","message" : "","msgcode" : ""}

    #ユーザーが存在するか
    is_registerd,user_obj = check_registerd_from_userid(friend_userid)

    #送信元通知
    sended_notify = {
        "msgcode" : "11132",
        "message" : "Failed to send friend request",
        "requestid" : ""
    }

    #ユーザーが登録されていなかったら
    if not is_registerd:
        sended_notify["message"] = "user not found"
        sended_notify["msgcode"] = "11139"

        await send_msg(userid,sended_notify)
        return

    #フレンドかどうか確認する
    is_friend,friend_data = check_friend(userid,friend_userid)

    #フレンドなら
    if is_friend:
        return_result["msgtype"] = "Friend_Error"
        return_result["message"] = "already friends"
        return_result["msgcode"] = "11118"
        return_result["friendid"] = str(friend_data.friendid)

        await send_msg(userid,return_result)
        return
    #リクエストが存在するか
    is_sended,request_data = check_request(userid,friend_userid)

    #存在する場合
    if is_sended:
        #送信者が一致する場合
        return_result["msgtype"] = "ServerMsg"
        return_result["requestid"] = str(request_data.requestid)
        if str(userid) == request_data.userid:
            #送信済みを返す
            return_result["msgcode"] = "11119"
            return_result["message"] = "Request has already been sent"
        else:
            #受信済みを返す
            return_result["msgcode"] = "11120"
            return_result["message"] = "Request already received"
        
        await send_msg(userid,return_result)
        return

    #フレンドリクエストを作成する
    is_success,resiter_data = create_request(userid,friend_userid)

    sended_notify["requestid"] = str(resiter_data.requestid)
    if is_success:
        #通知を作成する
        return_result["msgcode"] = "11121"
        return_result["message"] = "received a friend request"
        return_result["requestid"] = str(resiter_data.requestid)

        #通知を送信する
        await send_msg(friend_userid,return_result)
        
        sended_notify["message"] = "sent a friend request"
        sended_notify["msgcode"] = "11131"
        
    #送信元にも通知を送る
    await send_msg(userid,sended_notify)
#クライアントにメッセージを送信する
async def send_msg(sendid : str,msg):

    if sendid in websocket_clients:
        ws:WebSocket = websocket_clients[sendid]
        dump_msg = json.dumps(msg)

        #送信する
        await ws.send_text(dump_msg)
    
#接続切断
async def close_client(sendid : str):

    if sendid in websocket_clients:
        ws:WebSocket = websocket_clients[sendid]
        await ws.close()

#フレンドリクエスト承認
async def accept_friend_request(userid : str,requestid : str):
    return_result = {"msgtype" : "","message" : "","msgcode" : ""}

    #リクエストを承認する
    is_success,friend_data = accept_request(userid,requestid)

    #成功したら
    if is_success:
        return_result["msgtype"] = "Approval success"
        return_result["msgcode"] = "11123"
        return_result["friendid"] = str(friend_data.friendid)

        #フレンド通知
        notify_data = {
            "msgtype" : "friend request accepted",
            "msgcode" : "11124",
            "friendid" : str(friend_data.friendid)
        }

        #承認先に通知送信
        await send_msg(friend_data.friend_userid,notify_data)
    else:
        return_result["msgtype"] = "failed"
        return_result["msgcode"] = "11122"

    #承認もとに送信
    await send_msg(userid,return_result)
    
#フレンドリクエスト拒否
async def reject_friend_request(userid : str,requestid : str):
    return_result = {"msgtype" : "","message" : "","msgcode" : ""}
    is_success = reject_request(userid,requestid)

    if is_success:
        return_result["message"] = "Request reject Successfully"
        return_result["msgcode"] = "11125"
    else:
        return_result["message"] = "Failed to reject request"
        return_result["msgcode"] = "11125"
    
    return_result["rejectid"] = str(requestid)

    await send_msg(userid,return_result)

#フレンドリクエスト拒否
async def cancel_friend_request(userid : str,requestid : str):
    return_result = {"msgtype" : "","message" : "","msgcode" : ""}
    is_success = cancel_request(userid,requestid)

    if is_success:
        return_result["message"] = "Request canceled successfully"
        return_result["msgcode"] = "11128"
    else:
        return_result["message"] = "Failed to cancel request"
        return_result["msgcode"] = "11127"
    
    return_result["rejectid"] = str(requestid)

    await send_msg(userid,return_result)

#フレンドリクエスト拒否
async def delete_friend_user(userid : str,friendid : str):
    return_result = {"msgtype" : "","message" : "","msgcode" : ""}

    #フレンド情報を取得する
    is_friend,friend_data = get_info(userid,friendid)

    #フレンド情報が登録されてるか
    if not is_friend:
        return
    
    #フレンドを削除する
    is_success = delete_friend(friend_data.userid,friend_data.friend_userid)

    if is_success:
        return_result["message"] = "Friend deleted successfully"
        return_result["msgcode"] = "11129"
    else:
        return_result["message"] = "Failed to delete friend"
        return_result["msgcode"] = "11130"
    
    return_result["deleteid"] = str(friend_data.friendid)

    await send_msg(userid,return_result)

#フレンド一覧
async def ws_get_friends(userid : str):
    pass

#ここまで   

#Websocket
@app.websocket("/userws")
async def user_websocket_endpoint(ws : WebSocket):
    await ws.accept()

    #Websocketが認証済みか
    is_authed = False

    #認証ユーザ
    userid = ""

    while True:
        try:
            #受け取ってjsonに変換する
            data = await ws.receive_text()
            data_json = json.loads(data)

            #Websocketを認証する
            msgtype = data_json["msgtype"]
            if msgtype == "authToken":
                auth_result = {
                    "msgcode" : "",
                    "msgtype" : ""
                }

                #Websocket認証
                verify_result = token_util.verify_websocket_token(data_json["token"])
                if verify_result:
                    #認証済みにする
                    is_authed = True

                    #トークンをデコードする
                    decode_dict = dict(websocket_security._decode(data_json["token"]))
                    userid = str(decode_dict["subject"]["userid"])

                    #ユーザーが存在するか確認する
                    is_registred,user = check_registerd_from_userid(userid)
                    if is_registred:
                        #接続を記録する
                        websocket_clients[userid] = ws
                    else:
                        break
                    
                    auth_result["msgcode"] = "11111"
                    auth_result["msgtype"] = "authSuccess"
                else:
                    auth_result["msgcode"] = "11110"
                    auth_result["msgtype"] = "authFailed"
                
                #認証レスポンスを送信する
                auth_string = json.dumps(auth_result)
                await ws.send_text(auth_string)

                #認証が失敗したらループから抜ける
                if not verify_result:
                    break
            else:
                #認証済みでなければ抜ける
                if not is_authed:
                    break

                print(msgtype)
                #認証後の処理  
                if msgtype == "friend_request":
                    #送信先ID
                    sendid = data_json["friendid"]

                    #フレンドリクエストを送信する
                    await send_friend_request(userid,sendid)
                elif msgtype == "accept_request":
                    requestid = data_json["requestid"]

                    #フレンドリクエストを承認する
                    await accept_friend_request(userid,requestid)
                elif msgtype == "reject_request":
                    requestid = data_json["requestid"]

                    #フレンドリクエストを拒否する
                    await reject_friend_request(userid,requestid)
                elif msgtype == "cancel_request":
                    requestid = data_json["requestid"]

                    #フレンドリクエストを承認する
                    await cancel_friend_request(userid,requestid)
                elif msgtype == "remove_friend":
                    #フレンドを削除する
                    friendid = data_json["friendid"]

                    await delete_friend_user(userid,friendid)
                elif msgtype == "get_friends":
                    #フレンド
                    await ws_get_friends(userid)
        except:
            import traceback
            traceback.print_exc()
            
            break
    try:
        await ws.close()
    except:
        import traceback
        traceback.print_exc()
    try:
        websocket_clients.pop(userid)
    except:
        pass

#IOT用Websocket
@app.websocket("/iotws")
async def iot_websocket_endpoint(ws : WebSocket):
    await ws.accept()

    #Websocketが認証済みか
    is_authed = False

    while True:
        try:
            #受け取ってjsonに変換する
            data = await ws.receive_text()
            data_json = json.loads(data)

            #Websocketを認証する
            msgtype = data_json["msgtype"]
            if msgtype == "authToken":
                auth_result = {
                    "msgcode" : "",
                    "msgtype" : ""
                }

                #Websocket認証
                verify_result = False
                try:
                    decode_token = jwt.decode(data_json["token"],key=Iot_Token_Secret,algorithms=Iot_Token_Algorithm)
                    verify_result = True
                except:
                    import traceback
                    traceback.print_exc()

                if verify_result:
                    #認証済みにする
                    is_authed = True

                    #トークンをデコードする
                    decode_dict = dict(decode_token)
                    deviceid = str(decode_dict["deviceid"])

                    #ユーザーが存在するか確認する
                    is_registred,device = get_device(deviceid)
                    if is_registred:
                        #接続を記録する
                        websocket_clients[deviceid] = ws
                    else:
                        break
                    
                    auth_result["msgcode"] = "11111"
                    auth_result["msgtype"] = "authSuccess"
                else:
                    auth_result["msgcode"] = "11110"
                    auth_result["msgtype"] = "authFailed"
                
                #認証レスポンスを送信する
                auth_string = json.dumps(auth_result)
                await ws.send_text(auth_string)

                #認証が失敗したらループから抜ける
                if not verify_result:
                    break
            else:
                #認証済みでなければ抜ける
                if not is_authed:
                    break

                print(msgtype)
                #認証後の処理  
                
        except:
            import traceback
            traceback.print_exc()
            
            break
    try:
        await ws.close()
    except:
        import traceback
        traceback.print_exc()
    try:
        websocket_clients.pop(deviceid)
    except:
        pass

uvicorn.run(app,host="0.0.0.0",port=8000)#,ssl_keyfile="./server.key",ssl_certfile="./server.crt")
