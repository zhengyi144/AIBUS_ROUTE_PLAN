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
    data=request.get_json()
    #循环判断数据类型
    insertVals = []
    for item in data["items"]:
        if item["siteName"] =="" or item["siteName"] is None or\
           item["siteProperty"] =="" or item["siteProperty"] is None or\
           item["longitude"] =="" or item["longitude"] is None or \
           item["latitude"] =="" or item["latitude"] is None:
           res.update(code=ResponseCode.Fail,msg="名称经纬度站点属性字段不能为空！")
           return res.data
        else:
            siteProperty=1 if item["siteProperty"]=="固定" else 0
            #geojson = { "type": "Point", "coordinates": [float(item["longitude"]),float(item["latitude"])]}
            geojson = '{ "type": "Point", "coordinates": [%s, %s]}'%(float(item["longitude"]),float(item["latitude"]))
            insertVals.append((item["province"],item["city"],item["region"],item["siteName"],siteProperty,item["direction"],\
                float(item["longitude"]),float(item["latitude"]),item["road"],userInfo["citycode"],userInfo["userName"],userInfo["userName"],geojson))
    row=aiBusModel.batchStation(tuple(insertVals))
    if row>0:
        res.update(code=ResponseCode.Success, msg="成功插入{}条记录！".format(row))
        return res.data
    else:
        res.update(code=ResponseCode.Fail, msg="插入失败！")
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
        data=request.get_json()
        queryText=data['queryText']
        row=aiBusModel.selectStationNameByText(queryText,userInfo["citycode"],userInfo["userNames"])
        res.update(code=ResponseCode.Success, data=row)
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail,msg="站点名称模糊查询报错！")
        return res.data

@route(basicdata,'/queryStationList',methods=["POST"])
@login_required
def queryStationList():
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        province=data['province']
        city=data['city']
        siteName=data['siteName']
        road=data['road']
        siteStatus=data['siteStatus']
        pageSize=int(data['pageSize'])
        pageNum=int(data['pageNum'])-1
        count,row=aiBusModel.selectStationList(province,city,siteName,road,siteStatus,pageSize,pageNum,userInfo["citycode"],userInfo["userNames"]) 
        res.update(code=ResponseCode.Success, data={"count":count,"stationList":row})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail,msg="查询站点列表报错！")
        return res.data

@route(basicdata,'/upInsertStation',methods=["POST"])
@login_required
def upInsertStation():
    """
    新增或者更新站点
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        province=data['province']
        city=data['city']
        region=data["region"]
        siteName=data['siteName']
        siteProperty=data['siteProperty']
        road=data['road']
        siteStatus=data['siteStatus']
        latitude=float(data["latitude"])
        longitude=float(data["longitude"])
        direction=data["direction"]
        unilateral=data["unilateral"]
        upInsertType=data["upInsertType"]
        if siteName=="" or \
            siteProperty=="" or\
            latitude=="" or \
            longitude=="" or \
            direction=="" or \
            upInsertType=="":
            res.update(code=ResponseCode.Fail,msg="必填字段不可为空！")
            return res.data

        if siteProperty=="临时":
            siteProperty=0
        else:
            siteProperty=1
        
        if siteStatus=="停用":
            siteStatus=3
        elif siteStatus=="无效":
            siteStatus=2
        else:
            siteStatus=1
        
        if unilateral=="是":
            unilateral=1
        else:
            unilateral=0
        
        geojson = '{ "type": "Point", "coordinates": [%s, %s]}'% (longitude,latitude)
        if upInsertType=="I":
            #根据站点名称和地理方位保持唯一性
            row=aiBusModel.selectStationByNameDirection((siteName,direction))
            if row["num"]>0:
                res.update(code=ResponseCode.Fail,msg="该站点+地理方位己存在!")
                return res.data
            aiBusModel.insertStation((province,city,region,siteName,siteProperty,siteStatus,direction,longitude,latitude,road,unilateral,userInfo["citycode"],userInfo["userName"],userInfo["userName"]),geojson)
        else:
            id=data['id']
            if id is None or id=="":
                res.update(code=ResponseCode.Fail,msg="更新站点id不能为null")
                return res.data
            row=aiBusModel.updateStation((province,city,region,siteName,siteProperty,siteStatus,direction,longitude,latitude,road,unilateral,userInfo["citycode"],userInfo["userName"],id),geojson)
        res.update(code=ResponseCode.Success, msg="保存成功！")
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail,msg="站点新增/编辑报错！")
        return res.data

@route(basicdata,'/fuzzyQueryRoad',methods=["POST"])
@login_required
def fuzzyQueryRoad():
    """
    根据站点名称模糊查询站点
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        queryText=data['queryText']
        row=aiBusModel.selectRoadByText(queryText,userInfo["userNames"])
        res.update(code=ResponseCode.Success, data=row)
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail,msg="道路模糊查询报错！")
        return res.data

