import logging
from flask import Blueprint, jsonify, session, request, current_app

"""
基础数据维护模块api
"""
basicdata = Blueprint("basicdata", __name__, url_prefix='/basicdata')
logger = logging.getLogger(__name__)
