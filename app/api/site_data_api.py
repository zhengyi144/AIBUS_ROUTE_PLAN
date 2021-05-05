import logging
from flask import Blueprint, jsonify, session, request, current_app

"""
网点数据规划api
"""
sitedata = Blueprint("sitedata", __name__, url_prefix='/sitedata')
logger = logging.getLogger(__name__)
