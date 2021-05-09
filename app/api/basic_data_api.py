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
    """
    批量上传站点excel
    """
    res = ResMsg()
    aiBusModel=AiBusModel()
    userInfo = session.get("userInfo")
    #获取excel文件
    excelFile = request.files['file']
    dataset=readExcel(excelFile,0,"station")
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
            siteProperty=1 if item["siteProperty"]=="固定" else 0
            insertVals.append((item["province"],item["city"],item["region"],item["siteName"],siteProperty,item["location"],\
                float(item["longitude"]),float(item["latitude"]),item["road"],userInfo["citycode"]))
    row=aiBusModel.batchStation(tuple(insertVals))
    if row>0:
        res.update(code=ResponseCode.Success, data="成功插入{}条记录！".format(row))
        return res.data
    else:
        res.update(code=ResponseCode.Fail, data="插入失败！")
        return res.data

@route(basicdata,'/fuzzyQueryStationName',methods=["POST"])
@login_required
def fuzzyQueryStationName():
    """
    根据站点名称模糊查询站点
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        queryText=request.form.get('queryText')
        row=aiBusModel.selectStationNameByText(queryText,userInfo["citycode"])
        res.update(code=ResponseCode.Success, data=row)
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.QueryError)
        return res.data

@route(basicdata,'/queryStationList',methods=["POST"])
@login_required
def queryStationList():
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        province=request.form.get('province')
        city=request.form.get('city')
        siteName=request.form.get('siteName')
        road=request.form.get('road')
        siteStatus=request.form.get('siteStatus')
        pageSize=int(request.form.get('pageSize'))
        pageNum=int(request.form.get('pageNum'))
        row=aiBusModel.selectStationList(province,city,siteName,road,siteStatus,userInfo["citycode"],pageSize,pageNum)
        res.update(code=ResponseCode.Success, data=row)
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.QueryError)
        return res.data