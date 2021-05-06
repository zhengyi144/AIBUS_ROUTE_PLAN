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

@common.route('/logs', methods=["GET"])
def test_logger():
    """
    测试自定义logger
    :return:
    """
    logger.info("this is info")
    logger.debug("this is debug")
    logger.warning("this is warning")
    logger.error("this is error")
    logger.critical("this is critical")
    return "ok"

@route(common, '/typeResponse', methods=["GET"])
def test_type_response():
    """
    测试返回不同的类型
    :return:
    """
    res = ResMsg()
    now = datetime.now()
    date = datetime.now().date()
    num = Decimal(11.11)
    test_dict = dict(now=now, date=date, num=num)
    # 此处只需要填入响应状态码,即可获取到对应的响应消息
    res.update(code=ResponseCode.Success, data=test_dict)
    # 此处不再需要用jsonify，如果需要定制返回头或者http响应如下所示
    # return res.data,200,{"token":"111"}
    return res.data


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

@route(common, '/testGetData', methods=["GET"])
@login_required
def test_get_data():
    """
    测试登陆保护下获取数据
    :return:
    """
    res = ResMsg()
    userInfo = session.get("userInfo")
    res.update(data=userInfo)
    return res.data





