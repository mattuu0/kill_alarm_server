from database.models import iot_device,User,Friend
from friends.friend import check_friend

from database.setting import session

#IOTデバイスを登録する
def pair_device(deviceid:str,userid:str):
    #ユーザーが既にデバイスを登録しているか
    is_registered,device = get_device_from_userid(userid)

    #登録していたら
    if is_registered:
        return False,None

    #デバイスを取得する
    is_register,device = get_device(deviceid)
    
    #デバイスが存在する場合
    if is_register:
        #デバイスがまだペアリングさえれていなかったら
        if str(device.paring_userid) == "":
            device.paring_userid = str(userid)

            session.commit()

            return True,device
        
    return False,None

#IOTデバイスの登録を解除する
def unpair_device(userid:str):
    #デバイスを取得する
    is_register,device = get_device_from_userid(userid)
    
    #デバイスが存在する場合
    if is_register:
        device.paring_userid = ""

        session.commit()

        return True,device
        
    return False,None

#IOTデバイスを取得する
def get_device(deviceid : str):
    #デバイスを検索する
    device_filter = session.query(iot_device).filter(iot_device.deviceid == deviceid)

    #デバイスを存在するか
    get_device = device_filter.first()

    #デバイスが存在する場合
    if get_device:
        return True,get_device
    
    return False,None


#IOTデバイスを取得する
def get_device_from_userid(userid : str):
    #デバイスを検索する
    device_filter = session.query(iot_device).filter(iot_device.paring_userid == userid)

    #デバイスを存在するか
    get_device = device_filter.first()

    #デバイスが存在する場合
    if get_device:
        return True,get_device
    
    return False,None

#ユーザーを削除する
def delete_user(userid:str):
    unpair_device(userid)
