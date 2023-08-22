from sqlalchemy.schema import Column
from sqlalchemy.types import String,Boolean,DateTime,Integer
from datetime import datetime
import uuid
from sqlalchemy import Column,ForeignKey,Time
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType

from database.setting import Base,engine
from hashlib import sha3_256,sha3_512
import secrets

id_length = 64
def gen_uniqueid() -> str:
    userid = str(uuid.uuid4())
    return sha3_256(userid.encode("utf-8")).hexdigest()

#IOTデバイスのIDを生成する
def gen_iotid() -> str:
    userid = str(uuid.uuid4())
    secretid = secrets.token_bytes(128)
    return sha3_512(userid.encode("utf-8") + secretid).hexdigest()


#ユーザーモデル
class User(Base):
    __tablename__ = "user"  # テーブル名を指定
    userid = Column(String(id_length), primary_key=True, default=gen_uniqueid)  #ユーザID

    display_name = Column(String(255))                                          #表示名
    username = Column(String(255))                                              #ユーザー名 (検索に使う)
    password = Column(String)                                                   #パスワード

    refresh_tokenid = Column(String)                                            #リフレッシュトークンID
    access_tokenid = Column(String)                                             #アクセストークンID
    websocket_tokenid = Column(String)                                          #WebsocketトークンID
    is_active = Column(Boolean,default=True)                                    #有効化

    timers = relationship("TimerData",cascade="all",uselist=False)              #タイマー

#目覚ましデータ
class TimerData(Base):
    __tablename__ = "TimerData"
    timerid = Column(String(id_length), primary_key=True, default=gen_uniqueid)                             #識別ID
    userid = Column(String(id_length),ForeignKey(User.userid,ondelete="CASCADE"))

    call_time = Column(Time,default=datetime.now().time())                                                  #発動する時間

    payloads = relationship("Payload",cascade="all")                                                        #発動するペイロード

class Payload(Base):
    __tablename__ = "Timer Payload"
    payloadId = Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)                        #識別するID
    timerid = Column(String(id_length),ForeignKey(TimerData.timerid,ondelete="CASCADE"))                    #タイマーID

    afterTime = Column(Integer,default=0)                                                                   #何秒後に実行するか

    strength = Column(Integer,default=0)                                                                    #強さ 0 1 2

    payload_type = Column(String,default="water")                                                           #種類 water,light,sound,blow,vibration
#フレンドデータ 
class Friend(Base):
    __tablename__ = "friend"

    friendid = Column(String(id_length), default=gen_uniqueid,primary_key=True)                         #フレンドID
    userid = Column(String(id_length))                                                                  #フレンドユーザーID              
    friend_userid = Column(String(id_length))                                                           #フレンドユーザーID (相手のID)
    created_at = Column(DateTime,default=datetime.now(),nullable=False)                                 #フレンドになった時間

#フレンドリクエスト
class Friend_request(Base):
    __tablename__ = "friend_request"

    requestid = Column(String(id_length), default=gen_uniqueid,primary_key=True)                        #リクエストID
    userid = Column(String(id_length))                                                                  #フレンドユーザーID              
    friend_userid = Column(String(id_length))                                                           #フレンドユーザーID (相手のID)
    created_at = Column(DateTime,default=datetime.now(),nullable=False)                                 #フレンドになった時間

#IOTデバイスオブジェクト
class iot_device(Base):
    __tablename__ = "IOT_Device"                                                                        #IOTデバイス
    deviceid = Column(String(id_length),default=gen_iotid,primary_key=True)                             #デバイスID
    tokenid = Column(String)                                                                            #トークンID
    paring_userid = Column(String(id_length),default="")                                                #ペアリングしているユーザID

Base.metadata.create_all(bind=engine)
