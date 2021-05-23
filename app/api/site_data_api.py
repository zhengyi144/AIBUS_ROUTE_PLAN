import logging
from flask import Blueprint, jsonify, session, request, current_app
from pymysql import NULL
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.auth import login_required
from app.utils.util import route
from app.utils.tools import *
from app.models.ai_bus_model import AiBusModel

"""
网点数据规划api
"""
sitedata = Blueprint("sitedata", __name__, url_prefix='/sitedata')
logger = logging.getLogger(__name__)


@route(sitedata, '/uploadSiteExcel', methods=["POST"])
@login_required
def uploadSiteExcel():
    """
    批量上传网点excel
    """
    res = ResMsg()
    aiBusModel=AiBusModel()
    userInfo = session.get("userInfo")
    #获取excel文件
    excelFile = request.files['file']
    dataset=readExcel(excelFile,0,"site")
    #获取目的信息
    destination=request.form.get("destination")
    longitude=request.form.get("longitude")
    latitude=request.form.get("latitude")
    mapType=request.form.get("mapType")
    if destination is None or destination=="" or\
       longitude is None or longitude=="" or \
       latitude is None or latitude=="" or \
       mapType is None or mapType=="":
       res.update(code=ResponseCode.InsertValueIsNull)
       return res.data
    
    #先判断目的地网点是否存在,存在则覆盖
    siteFile=aiBusModel.selectSiteFileIdByFileName((destination))
    if siteFile is None or siteFile["id"] is None :
       aiBusModel.insertSiteFile((destination,0,0,destination,mapType,longitude,latitude,userInfo["citycode"],userInfo["userName"],userInfo["userName"]))
       siteFile=aiBusModel.selectSiteFileIdByFileName((destination))
    else:
        #更新网点状态，后面重新插入
        aiBusModel.updateSiteStatusByfieldId((3,siteFile["id"]))
    #循环判断数据类型
    insertVals = []
    for item in dataset:
        if item["siteName"] is None or item["siteName"] =="" or \
           item["longitude"] is None or item["longitude"] =="" or  \
           item["latitude"] is None or item["latitude"] =="" :
           res.update(code=ResponseCode.InsertValueIsNull)
           return res.data
        else:
            siteProperty=1 if item["siteProperty"]=="固定" else 0
            #geojson = { "type": "Point", "coordinates": [float(item["longitude"]),float(item["latitude"])]}
            geojson = '{ "type": "Point", "coordinates": [%s, %s]}'%(float(item["longitude"]),float(item["latitude"]))

            if "region" in item:
                region=item["region"]
            else:
                region=""
            if "clientName" in item:
                clientName=item["clientName"]
            else:
                clientName=""
            if "clientProperty" in item:
                clientProperty=item["clientProperty"]
            else:
                clientProperty=""
            if "clientAddress" in item:
                clientAddress=item["clientAddress"]
            else:
                clientAddress=""
            if "age" in item:
                age=item["age"]
            else:
                age=NULL
            if "grade" in item:
                grade=item["grade"]
            else:
                grade=""
            if "number" in item:
                number=item["number"]
            else:
                number=NULL
            if "others" in item:
                others=item["others"]
            else:
                others=NULL

            insertVals.append((siteFile["id"],region,item["siteName"],siteProperty,2,\
                float(item["longitude"]),float(item["latitude"]),clientName,clientProperty,clientAddress,age,grade,number,others,geojson))
    if len(insertVals)>0:
        #现将批量导入文件信息插入tbl_site_files,并更新tbl_site_files.fileStatus为有效文件
        aiBusModel.updateSiteFile((1,len(insertVals),siteFile["id"]))
        #此时tbl_site中siteStatus还是临时站点
        row=aiBusModel.batchSites(tuple(insertVals))
        if row>0:
            res.update(code=ResponseCode.Success, data="成功插入{}条记录！".format(row))
            return res.data
        else:
            res.update(code=ResponseCode.Fail, data="插入失败！")
            return res.data
    else:
        res.update(code=ResponseCode.Success, data="插入0条记录！")
        return res.data

@route(sitedata, '/querySiteFileList', methods=["POST"])
@login_required
def querySiteFileList():
    res = ResMsg()
    aiBusModel=AiBusModel()
    userInfo = session.get("userInfo")