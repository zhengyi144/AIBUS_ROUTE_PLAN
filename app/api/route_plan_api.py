import logging
from flask import Blueprint, jsonify, session, request, current_app
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.auth import login_required
from app.utils.util import route
from app.utils.tools import *
from app.models.ai_bus_model import AiBusModel
from app.algorithms.sa import tspSolution

"""
线路规划模块api
"""
routeplan = Blueprint("routeplan", __name__, url_prefix='/routeplan')
logger = logging.getLogger(__name__)

@route(routeplan, '/sortWayPoints', methods=["POST"])
@login_required
def sortWayPoints():
    """
    利用模拟退火算法对途经点进行排序
    """
    res = ResMsg()
    