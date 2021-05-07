import logging
from flask import Blueprint, jsonify, session, request, current_app
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.auth import Auth, login_required
from app.utils.util import route

"""
基础数据维护模块api
"""
basicdata = Blueprint("basicdata", __name__, url_prefix='/basicdata')
logger = logging.getLogger(__name__)

