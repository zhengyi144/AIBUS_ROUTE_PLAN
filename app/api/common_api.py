import logging
from datetime import datetime, timedelta
from decimal import Decimal
from flask import Blueprint, jsonify, session, request, current_app
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.auth import Auth, login_required
from app.utils.util import route

"""
通用功能api
"""
common = Blueprint("common", __name__, url_prefix='/common')
logger = logging.getLogger(__name__)

# --------------------JWT测试-----------------------------------------#
@route(common, '/login', methods=["POST"])
def login():
    """
    登陆成功获取到数据获取token和刷新token
    :return:
    """
    res = ResMsg()
    userName = request.form.get('userName')
    password = request.form.get("password")
    citycode = request.form.get("citycode")
    role= int(request.form.get("role"))
    # 未获取到参数或参数不存在
    if  not userName or not password or not citycode or role is None:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data
    auth = Auth()
    return auth.authenticate(userName,password,citycode,role)




