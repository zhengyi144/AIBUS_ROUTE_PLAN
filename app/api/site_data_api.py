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
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        #获取excel文件
        #excelFile = request.files['file']
        #dataset=readExcel(excelFile,0,"site")
        #获取目的信息
        data=request.get_json()
        destination=data["destination"]
        longitude=data["longitude"]
        latitude=data["latitude"]
        mapType=data["mapType"]
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
            #失效该文件对应所有临时site，后面重新插入
            aiBusModel.updateSiteStatusByfieldId((3,userInfo["userName"],siteFile["id"],2))
        #循环判断数据类型
        insertVals = []
        for item in data["items"]:
            if item["siteName"] is None or item["siteName"] =="" or \
               item["longitude"] is None or item["longitude"] =="" or  \
               item["latitude"] is None or item["latitude"] =="" :
               res.update(code=ResponseCode.InsertValueIsNull)
               return res.data
            else:
                if item["siteProperty"]=="固定":
                    siteProperty=1 
                elif item["siteProperty"]=="临时":
                    siteProperty=0
                else:
                    siteProperty=2
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
                    number=int(item["number"])
                else:
                    number=0
                if "others" in item:
                    others=item["others"]
                else:
                    others=NULL

                insertVals.append((siteFile["id"],region,item["siteName"],siteProperty,2,\
                    float(item["longitude"]),float(item["latitude"]),clientName,clientProperty,clientAddress,age,grade,number,others,userInfo["userName"],userInfo["userName"],geojson))
        if len(insertVals)>0:
            #现将批量导入文件信息插入tbl_site_files,并更新tbl_site_files.fileStatus为有效文件
            aiBusModel.updateSiteFile((1,len(insertVals),siteFile["id"]))
            #此时tbl_site中siteStatus还是临时站点
            row=aiBusModel.batchSites(tuple(insertVals))
            if row>0:
                res.update(code=ResponseCode.Success, data={"fileId":siteFile["id"], "fileName":destination,"siteCount":row})
                return res.data
            else:
                res.update(code=ResponseCode.Fail, data="插入失败！")
                return res.data
        else:
            res.update(code=ResponseCode.Success, data={"fileId":siteFile["id"], "fileName":destination,"siteCount":0})
            return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, data="插入失败！")
        return res.data

@route(sitedata, '/querySiteFileList', methods=["POST"])
@login_required
def querySiteFileList():
    """
    根据用户权限查询文件列表
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        siteFileList=aiBusModel.selectSiteFileList(userInfo["citycode"],userInfo["userNames"])
        res.update(code=ResponseCode.Success, data=siteFileList)
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, data="查询报错！")
        return res.data

@route(sitedata, '/fuzzyQuerySiteFileList', methods=["POST"])
@login_required
def fuzzyQuerySiteFileList():
    """
    根据用户权限+文件名称文本模糊查询文件列表
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        queryText=request.get_json()["queryText"]
        siteFileList=aiBusModel.fuzzyQuerySiteFileList(queryText,userInfo["citycode"],userInfo["userNames"])
        res.update(code=ResponseCode.Success, data=siteFileList)
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, data="查询报错！")
        return res.data

@route(sitedata, '/queryConfirmedSiteInfo', methods=["POST"])
def queryConfirmedSiteInfo():
    """
    根据网点文件id查询网点数据(返回已经确认导入的数据)
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        data=request.get_json()
        fileId=int(data["fileId"])
        siteInfo=aiBusModel.selectSiteInfoByFileId((fileId))
        res.update(code=ResponseCode.Success, data=siteInfo)
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, data="查询报错！")
        return res.data

@route(sitedata, '/queryTempSiteInfo', methods=["POST"])
def queryTempSiteInfo():
    """
    根据网点文件id查询网点数据(返回未确认的数据)
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        data=request.get_json()
        fileId=int(data["fileId"])
        pageSize=int(data['pageSize'])
        pageNum=int(data['pageNum'])
        kwargs={}
        if "region" in data:
            region=data['region'] #区域
            kwargs["region"]=region
        if "siteProperty" in data:
            kwargs["siteProperty"]=1 if data["siteProperty"]=="固定" else 0  #公交站点属性
        if "clientName" in data:
            kwargs["clientName"]=data['clientName']  #客户姓名
        if "clientProperty" in data:
            kwargs["clientProperty"]=data['clientProperty']  #客户属性
        if "age" in data:
            kwargs["age"]=data['age']  #客户年龄
        if "grade" in data:
            kwargs["grade"]=data['grade']  #客户年级
        if "number" in data:
            kwargs["number"]=data['number']  #客户年级
        
        siteInfo=aiBusModel.selectTempSiteInfo(fileId,kwargs,pageSize,pageNum)
        res.update(code=ResponseCode.Success, data=siteInfo)
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, data="查询报错！")
        return res.data
    
@route(sitedata, '/saveSiteList', methods=["POST"])
@login_required
def saveSiteList():
    """
    根据网点id保存网点信息：
    1)先失效原先文件对应的网点
    2)再更新新的网点
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        fileId=int(data["fileId"])
        siteIdList=data["siteIdList"]
        #siteIdList=list(map(int, request.form.get("siteIdList").split(",")))
        aiBusModel.updateSiteStatusByfieldId((3,userInfo["userName"],fileId,1))
        row=aiBusModel.updateSiteStatusByIds(fileId,1,siteIdList,userInfo["userName"])
        res.update(code=ResponseCode.Success, data="保存网点{}条".format(row))
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, data="保存报错！")
        return res.data

@route(sitedata, '/deleteSite', methods=["POST"])
@login_required
def deleteSite():
    """
    删除单个网点接口
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        fileId=data["fileId"]
        siteName=data["siteName"]
        latitude=float(data["latitude"])
        longitude=float(data["longitude"])
        row=aiBusModel.invalidSiteBySiteName((3,userInfo["userName"],siteName,fileId,longitude,latitude))
        res.update(code=ResponseCode.Success, data="删除网点{}条".format(row))
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, data="删除出错！")
        return res.data