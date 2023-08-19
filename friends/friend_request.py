from database.models import Friend,Friend_request
from .friend import check_friend,create_friend
from database.setting import session
from sqlalchemy import or_

#リクエストが既に送信済みか
def check_request(userid:str,friend_userid:str):
    #フレンドリクエスト情報を検索する
    friend_filter = session.query(Friend_request).filter(or_(Friend_request.friend_userid == userid,Friend_request.userid == userid))

    request_data = friend_filter.first()

    #リクエスト情報があったら
    if request_data:
        #情報があっているか
        if str(request_data.friend_userid == friend_userid) or str(request_data.userid == friend_userid):
            return True,request_data
        else:
            return False,None
    else:
        return False,None

#リクエストを送信する
def create_request(userid:str,friend_userid:str):
    #フレンドかどうか確認する
    is_friend,friend_data = check_friend(userid,friend_userid)
    #フレンドなら戻る
    if is_friend:
        return False,None

    is_sended,request_data = check_request(userid,friend_userid)

    #送信済みなら既存のリクエストを返す
    if is_sended:
        return False,request_data
    
    #登録するリクエスト
    register_data = Friend_request()
    register_data.friend_userid = friend_userid
    register_data.userid = userid

    #リクエストを登録する
    session.add(register_data)
    session.commit()

    return True,register_data

#フレンドリクエストを承認する
def accept_request(userid:str,requestid:str):
    #リクエストが存在するか
    friend_filter = session.query(Friend_request).filter(Friend_request.requestid==requestid)

    request_data = friend_filter.first()

    #リクエストが存在したら
    if request_data:
        #リクエスト情報と受信者が一致したら
        if str(userid) == str(request_data.friend_userid):

            #フレンドかどうか確認する
            is_friend,friend_data = check_friend(request_data.userid,userid)
            #フレンドなら戻る
            if is_friend:
                return False,None
            
            #フレンド情報を登録する
            friend_data = create_friend(userid,request_data.userid)
            #リクエストを削除する
            session.delete(request_data)
            session.commit()

            return True,friend_data
    
    return False,None

#リクエストをキャンセルする
def cancel_request(userid : str,requestid : str):
    #リクエストを検索する
    friend_filter = session.query(Friend_request).filter(Friend_request.requestid==requestid)

    request_data = friend_filter.first()

    #リクエストが存在したら
    if request_data:
        #送信者を確かめる

        if str(request_data.userid) == str(userid):
            #送信者が一致したら削除する
            session.delete(request_data)
            session.commit()

            return True
        
    return False

#リクエストを拒否する
def reject_request(userid : str,requestid : str):
    #リクエストを検索する
    friend_filter = session.query(Friend_request).filter(Friend_request.requestid==requestid)

    request_data = friend_filter.first()

    #リクエストが存在したら
    if request_data:
        #受信者を確かめる
        if str(request_data.friend_userid) == str(userid):
            #受信者が一致したら削除する
            session.delete(request_data)
            session.commit()

            return True
        
    return False

#リクエストを削除する
def delete_user(userid :str):
    friend_filter = session.query(Friend_request).filter(or_(Friend_request.friend_userid == userid,Friend_request.userid == userid))

    #関連するフレンドリクエストを全て削除する
    for friend_data in friend_filter.all():
        session.delete(friend_data)
    session.commit()