from database.models import Friend
from database.setting import session
from sqlalchemy import or_

#フレンドかどうか確認する
def check_friend(userid:str,friend_userid:str):
    #フレンド情報を検索する
    friend_filter = session.query(Friend).filter(or_(Friend.friend_userid == userid,Friend.userid == userid))

    friend_data = friend_filter.first()

    #フレンド情報があったら
    if friend_data:
        #情報があっているか
        if str(friend_data.friend_userid == friend_userid) or str(friend_data.userid == friend_userid):
            #フレンドになっているか
            return True,friend_data
        else:
            return False,None
    else:
        return False,None

#ユーザーを削除する際にフレンドを削除する
def delete_user(userid : str):
    friends = session.query(Friend).filter(or_(Friend.friend_userid == userid,Friend.userid == userid))

    for friend_data in friends.all():
        session.delete(friend_data)
    session.commit()

#フレンドにする
def create_friend(userid:str,friend_userid:str) -> Friend:
    #フレンドかどうか
    is_friend,friend = check_friend(userid,friend_userid)

    #フレンドなら
    if is_friend:
        return friend

    else:
        #登録するフレンド情報
        friend_data = Friend()
    
        friend_data.userid = userid                 #登録するユーザーID
        friend_data.friend_userid = friend_userid   #登録されるユーザーID

        session.add(friend_data)
        session.commit()
    
        return friend_data

#フレンドを削除する
def delete_friend(userid:str,friend_userid:str) -> bool:
    #フレンドかどうか
    is_friend,friend = check_friend(userid,friend_userid)

    #フレンドなら
    if is_friend:
        session.delete(friend)
        session.commit()

        return True
    else:
        return False

#フレンド一覧を取得する
def get_friends(userid : str):
    friends = session.query(Friend).filter(or_(Friend.friend_userid == userid,Friend.userid == userid))

    return_dict = {"msgcode":"11144","friends":[]}
    
    #フレンド情報を追加する
    for friend in friends.all():
        friend_dict = {
            "friendid":friend.friendid,                     #相手のID
            "friend_userid" : friend.friend_userid,         
            "friended_at" : friend.created_at.timestamp()
        }
        
        return_dict["friends"].append(friend_dict)
    
    return return_dict
#IDからフレンド情報を取得する
def get_info(userid:str,friendid:str):
    #フレンド情報を検索する
    friend_filter = session.query(Friend).filter(Friend.friendid==friendid)

    friend_data = friend_filter.first()

    if friend_data:
        #ユーザーIDに含まれるか
        if friend_data.userid == userid or friend_data.friend_userid == userid:
            return True,friend_data
        
    return False,None