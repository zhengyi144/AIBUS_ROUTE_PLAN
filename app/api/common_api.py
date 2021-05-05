import logging
from flask import Blueprint, jsonify, session, request, current_app

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




