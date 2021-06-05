import logging
from flask import Blueprint, jsonify, session, request, current_app
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.auth import login_required
from app.utils.util import route
from app.utils.tools import *
from app.models.ai_bus_model import AiBusModel

"""
聚类模块api
"""
cluster = Blueprint("cluster", __name__, url_prefix='/cluster')
logger = logging.getLogger(__name__)