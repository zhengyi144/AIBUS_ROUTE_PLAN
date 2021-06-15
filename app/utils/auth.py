from re import sub
import jwt
import logging
from datetime import datetime, timedelta
from flask import current_app, request, session
from functools import wraps
from app.utils.code import ResponseCode
from app.utils.core import JSONEncoder
from app.utils.response import ResMsg
from app.models.ai_bus_model import AiBusModel

logger = logging.getLogger(__name__)

class Auth(object):
    key="auth##"
    @classmethod
    def encode_auth_token(cls, userName: str,
                          citycode:str,
                          exp: float = 24,
                          algorithm: str = 'HS256'):
        """
        userName: 用户名称
        password: 用户密码，现在暂未加密
        citycode: 用户所在城市编码
        role: 用户角色
        exp: access_token过期时间
        algorithm: 加密算法
        :return: 生成认证token
        """
        key = current_app.config.get('SECRET_KEY', cls.key)
        now = datetime.utcnow()
        exp_datetime = now + timedelta(hours=exp)
        access_payload = {
            'exp': int(datetime.timestamp(exp_datetime)),
            'flag': 0,  # 标识是否为一次性token，0是，1不是
            'iat': int(datetime.timestamp(now)),  # 开始时间
            'iss': 'qin',  # 签名
            'data':{
                'userName':userName,
                'citycode':citycode
                #'role': role
            }
        }
        access_token = jwt.encode(access_payload, key, algorithm=algorithm,json_encoder=JSONEncoder)#
        #payload = jwt.decode(access_token, key=key, options={'verify_exp': False},algorithms='HS256')
        #print(access_token,payload)
        return access_token

    @classmethod
    def decode_auth_token(cls, token: str,algorithm: str = 'HS256'):
        """
        验证token
        :param token:
        :return:
        """
        key = current_app.config.get('SECRET_KEY', cls.key)
        try:
            # 取消过期时间验证
            payload = jwt.decode(token, key=key, options={'verify_exp': False},algorithms='HS256')
            #payload = jwt.decode(token, key=key ,algorithms=algorithm)
        except jwt.ExpiredSignatureError:
            logger.error("token验证超时！")
            return None
        except jwt.InvalidTokenError:
            logger.error("无效token！")
            return None
        except jwt.InvalidSignatureError:
            logger.error("token签名错误！")
            return None
        else:
            return payload
    
    def authenticate(self,userName,password,citycode):
        """
        用户登录认证，登录成功返回token,登录失败返回失败原因
        """
        res = ResMsg()
        aiBusModel=AiBusModel()
        matchUser=aiBusModel.selectUserByUserInfo(userName,password)
        #print(matchUser)
        if not matchUser:
            res.update(code=ResponseCode.AccountOrPassWordErr)
            return res.data
        else:
            token=self.encode_auth_token(userName,citycode)
            res.update(code=ResponseCode.Success,data={"token":token})
            return res.data
    
    def identify(self, auth_header):
        """
        用户鉴权
        :return: list
        """
        aiBusModel=AiBusModel()
        if auth_header:
            payload = self.decode_auth_token(auth_header)
            if payload is None:
                return False
            if "data" in payload and "flag" in payload:
                if payload["flag"] == 0:
                    #获取用户所有下级
                    userInfo=payload["data"]
                    subUsers=aiBusModel.selectSubUserByUserName(userInfo["userName"],userInfo["citycode"])
                    userNames=[]
                    for user in subUsers:
                        userNames.append(user["userName"])
                    userNames.append(userInfo["userName"])
                    return {"userName":userInfo["userName"],"userNames":userNames,"citycode":userInfo["citycode"]}
                else:
                    # 其他状态暂不允许
                    return False
            else:
                return False
        else:
            return False

def login_required(f):
    """
    登陆保护，验证用户是否登陆
    :param f:
    :return:
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        res = ResMsg()
        token = request.headers.get("Authorization", default=None)
        if not token:
            res.update(code=ResponseCode.PleaseSignIn)
            return res.data
        auth = Auth()
        userInfo = auth.identify(token)
        if not userInfo:
            res.update(code=ResponseCode.PleaseSignIn)
            return res.data
        # 获取到用户信息('userName', 'userNames','citycode')并写入到session中,方便后续使用
        session["userInfo"] = userInfo
        return f(*args, **kwargs)
    return wrapper
