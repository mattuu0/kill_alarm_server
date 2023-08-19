from .hash import Hash
from database.models import User
from database.setting import session

#登録されているかを名前で確認
def check_registerd_from_username(username : str):    
    user_filter = session.query(User).filter(User.username == username)
    user_obj = user_filter.first()

    if user_obj:
        return True,user_obj
    else:
        return False,None
    
#登録されているかをユーザーIDで確認
def check_registerd_from_userid(userid : str):    
    user_filter = session.query(User).filter(User.userid == userid)
    user_obj = user_filter.first()

    if user_obj:
        return True,user_obj
    else:
        return False,None


def create_user(username : str,password : str) -> User:
    #ユーザーが存在するか確認
    is_registered,user = check_registerd_from_username(username)

    #存在するならユーザを返す
    if is_registered:
        return user
    
    #ユーザーが存在しない場合新規作成する
    save_user = User()      #保存するユーザーオブジェクト

    save_user.username = username

    save_user.password = Hash.get_password_hash(password)

    #ユーザー追加
    session.add(save_user)
    
    #保存
    session.commit()

    return save_user

#ユーザーIDからユーザーを取得する
def get_user(userid : str):
    is_registered,user = check_registerd_from_userid(userid)

    if is_registered:
        return user
    else:
        return None

def auth_login(username : str,password : str):
    #登録されいるか
    is_registered,user = check_registerd_from_username(username)

    #登録されていたら
    if is_registered:
        #パスワードがあっていたら
        if Hash.verify_password(user.password,password):
            return True,user
        
    return False,None

#ユーザーを削除する
def delete_user(userid : str):
    is_registered,user = check_registerd_from_userid(userid)

    if is_registered:
        session.delete(user)

        session.commit()