from typing import Set
from flask import Blueprint, jsonify, session, request, current_app
from numpy import array
from pymysql import NULL
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.auth import login_required
from app.utils.util import route
from app.utils.tools import *
from app.utils.GPSConvertUtil import *
from app.utils.logger import get_logger
from app.models.ai_bus_model import AiBusModel


"""
网点数据规划api
"""
sitedata = Blueprint("sitedata", __name__, url_prefix='/sitedata')
logger=get_logger(name="sitedata",log_file="logs/logger.log")


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
        siteFile=aiBusModel.selectSiteFileIdByFileName((destination),[1,2],userInfo["userNames"])
        if siteFile is None or siteFile["id"] is None or siteFile["fileStatus"]==2 :
           aiBusModel.insertSiteFile((destination,0,0,0,destination,mapType,longitude,latitude,userInfo["citycode"],userInfo["userName"],userInfo["userName"]))
           siteFile=aiBusModel.selectSiteFileIdByFileName((destination),[0],userInfo["userNames"])
        elif siteFile["fileStatus"]==1:
            res.update(code=ResponseCode.Fail, msg="重复插入网点文件！")
            return res.data
            #失效该文件对应所有临时site，后面重新插入
            #aiBusModel.updateSiteStatusByfieldId((3,userInfo["userName"],siteFile["id"],2))
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
                
                #根据mapType进行坐标转换
                if int(mapType)==2:
                    #百度地图
                    lng,lat=convert_BD09_to_GCJ02(float(item["longitude"]),float(item["latitude"]))
                else:
                    lng=float(item["longitude"])
                    lat=float(item["latitude"])

                #geojson = { "type": "Point", "coordinates": [float(item["longitude"]),float(item["latitude"])]}
                #geojson = '{ "type": "Point", "coordinates": [%s, %s]}'%(lng,lat)

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
                if "number" in item and isinstance(item["number"],int):
                    number=int(item["number"])
                elif clientName!="":
                    number=1
                else:
                    number=0
                if "others" in item:
                    others=item["others"]
                else:
                    others=NULL

                insertVals.append((siteFile["id"],region,item["siteName"],siteProperty,2,\
                    lng,lat,clientName,clientProperty,clientAddress,age,grade,number,others,\
                    userInfo["userName"],userInfo["userName"],float(item["longitude"]),float(item["latitude"])))
        if len(insertVals)>0:
            #此时tbl_site中siteStatus还是临时站点
            row=aiBusModel.batchSites(tuple(insertVals))
            #现将批量导入文件信息插入tbl_site_files,并更新tbl_site_files.fileStatus为临时文件2
            aiBusModel.updateSiteFile((2,0,userInfo["userName"],siteFile["id"]))
            if row>0:
                res.update(code=ResponseCode.Success, data={"fileId":siteFile["id"], "fileName":destination,"siteCount":0})
                return res.data
            else:
                res.update(code=ResponseCode.Fail, msg="插入失败！")
                return res.data
        else:
            res.update(code=ResponseCode.Success, data={"fileId":siteFile["id"], "fileName":destination,"siteCount":0})
            return res.data
    except Exception as e:
        logger.error("uploadSiteExcel exception:{}".format(str(e)))
        res.update(code=ResponseCode.Fail, msg="网点插入报错！")
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
        data=request.get_json()
        #根据fileType来判断聚类文件是否展开
        fileType=int(data["fileType"])
        userInfo = session.get("userInfo")
        if fileType==1:
            siteFileList=aiBusModel.selectFileList(userInfo["citycode"],userInfo["userNames"])
        else:
            siteFileList=aiBusModel.selectSiteFileList(userInfo["citycode"],userInfo["userNames"])
        res.update(code=ResponseCode.Success, data=siteFileList)
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, msg="网点文件查询报错！")
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
        res.update(code=ResponseCode.Fail, msg="网点文件模糊查询报错！")
        return res.data

@route(sitedata,'/fuzzyQuerySiteName', methods=["POST"])
@login_required
def fuzzyQuerySiteName():
    """
    根据网点名称模糊查询即将导入的网点
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        queryText=data['queryText']
        fileId=data["fileId"]
        row=aiBusModel.selectSiteNameByText(queryText,fileId,2)
        res.update(code=ResponseCode.Success, data=row)
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail,msg="模糊查询网点名称报错！")
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
        fileId=data["fileId"]
        siteParams=aiBusModel.selectClusterParams((fileId))##根据网点文件fileId的查询网点文件
        if siteParams:
            #查询聚类点
            clusterInfo=aiBusModel.selectClusterSiteInfoByFileId((fileId))
            res.update(code=ResponseCode.Success, data=clusterInfo)
        else:
            siteInfo=aiBusModel.selectSiteInfoByFileId((fileId))
            res.update(code=ResponseCode.Success, data=siteInfo)
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, msg="查询网点信息报错！")
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
        #pageSize=int(data['pageSize'])
        #pageNum=int(data['pageNum'])-1    #pageNum前端是从1开始
        kwargs={}
        if "siteName" in data and data["siteName"]:
            kwargs["siteName"]=data["siteName"]

        if "region" in data and isinstance(data["siteName"],list) and len(data["siteName"])>0:
            region=data['region'] #区域
            kwargs["region"]=region

        if "siteProperty" in data and isinstance(data["siteProperty"],list) and len(data["siteProperty"])>0:
            siteProperty=[]
            for item in data["siteProperty"]:
                if item=="固定":
                    siteProperty.append(1)
                elif item=="临时":
                    siteProperty.append(0)
                else:
                    siteProperty.append(2)
                    
            kwargs["siteProperty"]=siteProperty  #公交站点属性
        
        if "clientName" in data and isinstance(data["clientName"],list) and len(data["clientName"])>0:
            kwargs["clientName"]=data['clientName']  #客户姓名
        
        if "clientProperty" in data and isinstance(data["clientProperty"],list) and len(data["clientProperty"])>0:
            kwargs["clientProperty"]=data['clientProperty']  #客户属性
        
        if "age" in data and isinstance(data["age"],list) and len(data["age"])>0:
            kwargs["age"]=data['age']  #客户年龄
        
        if "grade" in data and isinstance(data["grade"],list) and len(data["grade"])>0:
            kwargs["grade"]=data['grade']  #客户年级
        
        if "number" in data and isinstance(data["number"],list) and len(data["number"])>0:
            kwargs["number"]=data['number']  #客户年级
        
        siteInfo=aiBusModel.selectTempSiteInfo(fileId,kwargs)
        
        #查询自定义项
        customInfo=aiBusModel.selectCustomSiteInfo(fileId)
        customItem={"siteProperty":set(),"region":set(), "clientName":set(),\
            "clientProperty":set(),"age":set(),"clientAddress":set(),"number":set(),"grade":set()}
        for item in customInfo:
            for key in customItem.keys():
                if item[key]!="":
                    customItem[key].add(item[key])
        #将set转为list
        for key in customItem.keys():
            customItem[key]=list(customItem[key])

        res.update(code=ResponseCode.Success, data={"siteInfo":siteInfo,"customItem":customItem})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, msg="查询临时网点信息报错！")
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
        aiBusModel.updateSiteStatusByfieldId((0,userInfo["userName"],fileId,1))
        row=aiBusModel.updateSiteStatusByIds(fileId,1,siteIdList,userInfo["userName"])
        #更新网点文件sitecount
        client=aiBusModel.selectSiteClientNumberByFileId(fileId)
        aiBusModel.updateSiteFile((1,client["clientNumber"],userInfo["userName"],fileId))

        res.update(code=ResponseCode.Success, msg="保存网点{}条".format(row))
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, msg="保存网点信息报错！")
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
        siteList=data["siteList"]
        for item in siteList:
            siteName=item["siteName"]
            latitude=float(item["latitude"])
            longitude=float(item["longitude"])
            row=aiBusModel.invalidSiteBySiteName((3,userInfo["userName"],siteName,fileId,longitude,latitude))
            #失效网点后需要更新对应的网点文件siteCount
            if row>0:
                #更新网点文件sitecount
                client=aiBusModel.selectSiteClientNumberByFileId(fileId)
                aiBusModel.updateSiteFile((1,client["clientNumber"],userInfo["userName"],fileId))
        res.update(code=ResponseCode.Success, msg="删除网点成功！")
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, msg="删除网点报错！")
        return res.data

@route(sitedata,'/exportSitePoints',methods=["POST"])
@login_required
def exportSitePoints():
    """
    根据网点文件id导出网点和聚类信息
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        fileId=data["fileId"]
        # print(fileId)
        sitefileList=aiBusModel.searchSiteListByFileId(fileId)
        if sitefileList is None:
            sitefileList=[]
        # 聚类文件导出
        #clusterInfo = aiBusModel.searchClusterResult(fileId)
        res.update(code=ResponseCode.Success, data={"siteResult":sitefileList})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data

#-----------------------设置站点样式------------------------------------#
@route(sitedata,'/saveStationStyle',methods=["POST"])
def saveStationStyle():
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        data=request.get_json()
        style=data["style"]
        
        #先删除再插入
        aiBusModel.deleteStationStyle()
        aiBusModel.insertStationStyle((json.dumps(style)))
        res.update(code=ResponseCode.Success, msg="保存样式成功！")
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data

@route(sitedata,'/getStationStyle',methods=["POST"])
def getStationStyle():
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        row=aiBusModel.selectStationStyle()
        res.update(code=ResponseCode.Success,data=row)
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data
    