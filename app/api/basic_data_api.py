import logging
from flask import Blueprint, jsonify, session, request, current_app
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.auth import login_required
from app.utils.util import route
from app.utils.tools import *
from app.models.ai_bus_model import AiBusModel

"""
基础数据维护模块api
"""
basicdata = Blueprint("basicdata", __name__, url_prefix='/basicdata')
logger = logging.getLogger(__name__)


@route(basicdata, '/uploadStationExcel', methods=["POST"])
@login_required
def uploadStationExcel():
    res = ResMsg()
    userInfo = session.get("userInfo")
    #获取excel文件
    excelFile = request.files['file']
    dataset=readExcel(excelFile,0,"station")
    print(dataset)
    #循环判断数据类型
    insertVals = []
    for item in dataset:
        if item["siteName"] =="" or item["siteName"] is None or\
           item["siteProperty"] =="" or item["siteProperty"] is None or\
           item["longitude"] =="" or item["longitude"] is None or \
           item["latitude"] =="" or item["latitude"] is None:
           res.update(code=ResponseCode.InsertValueIsNull)
           return res.data
        else:
            insertVals.append((item["province"],item["city"],item["region"],item["siteName"],item["siteProperty"],item["location"],\
                float(item["longitude"]),float(item["latitude"]),item["road"],userInfo["citycode"]))

    aiBusModel=AiBusModel()
    row=aiBusModel.insertStation(tuple(insertVals))
    if row>0:
        res.update(code=ResponseCode.Success, data="成功插入{}条记录！".format(row))
        return res.data
    else:
        res.update(code=ResponseCode.Fail, data="插入失败！")
        return res.data

        
