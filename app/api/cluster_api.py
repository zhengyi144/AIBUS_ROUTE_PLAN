import logging
from flask import Blueprint, jsonify, session, request, current_app
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.auth import login_required
from app.utils.util import route
from app.utils.tools import *
from app.models.ai_bus_model import AiBusModel
from app.algorithms.dbscan import clusterByDbscan

"""
聚类模块api
"""
cluster = Blueprint("cluster", __name__, url_prefix='/cluster')
logger = logging.getLogger(__name__)


@route(cluster,'/generateClusterPoints',methods=["POST"])
@login_required
def generateClusterPoints():
    """
    根据网点文件id生成聚类点
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        fileId=data["fileId"]
        epsRadius=float(data["epsRadius"])
        minSamples=data["minSamples"]
        #先判断网点文件是否有效
        fileStatus=aiBusModel.selectSiteFileStatus(fileId)
        if fileStatus["fileProperty"]==0:
            res.update(code=ResponseCode.Fail,data="该网点文件还未确认导入!")
            return res.data
        if fileStatus["fileStatus"]==0:
            res.update(code=ResponseCode.Fail,data="该网点文件已经失效!")
            return res.data
        #判断该网点文件是否已经聚类过,聚类过则对结果进行失效
        aiBusModel.invalidClusterSitesByFileId((userInfo["userName"],fileId))

        #根据网点文件查询网点list
        siteGeoList=aiBusModel.selectSiteGeoListByFileId(fileId)
        clusterInfo=clusterByDbscan(siteGeoList,epsRadius/1000,minSamples)
        #将聚类结果保存至表中
        insertVals=[]
        siteGeoDict={}
        for site in siteGeoList:
            siteGeoDict[str(site["id"])]=site
        
        clusterOutPoints=[]
        clusterCorePoints=[]
        clusterAroundPoints=[]
        #1)处理异常点fileId,siteId,clusterName,clusterProperty,clusterStatus,longitude,latitude,number,siteSet
        for id in clusterInfo["noiseIds"]:
            relativeId="site_"+str(id)
            site=siteGeoDict[str(id)]
            insertVals.append((fileId,relativeId,site["siteName"],0,1,site["lng"],site["lat"],site["number"],"",userInfo["userName"],userInfo["userName"]))
            clusterOutPoints.append({"id":relativeId,"siteName":site["siteName"],"number":site["number"],"longitude":site["lng"],"latitude":site["lat"]})

        #2)处理聚类点
        for cluster in clusterInfo["clusterSet"]:
            #处理聚类核心点
            clusterNumber=0
            clusterId=int(cluster["clusterCenterId"])
            site=siteGeoDict[str(clusterId)]
            for id in cluster["clusterCoreIds"]:
                clusterNumber+=siteGeoDict[str(id)]["number"]
            insertVals.append((fileId,"site_"+str(clusterId),site["siteName"],1,1,site["lng"],site["lat"],clusterNumber,",".join(map(str, cluster["clusterCoreIds"])),userInfo["userName"],userInfo["userName"]))
            clusterCorePoints.append({"id":"site_"+str(clusterId),"siteName":site["siteName"],"number":clusterNumber,"longitude":site["lng"],"latitude":site["lat"]})
            #处理边界点
            for id in cluster["clusterAroundIds"]:
                relativeId="site_"+str(id)
                aroundSite=siteGeoDict[str(id)]
                insertVals.append((fileId,relativeId,aroundSite["siteName"],2,1,aroundSite["lng"],aroundSite["lat"],aroundSite["number"],"",userInfo["userName"],userInfo["userName"]))
                clusterAroundPoints.append({"id":relativeId,"siteName":aroundSite["siteName"],"number":aroundSite["number"],"longitude":aroundSite["lng"],"latitude":aroundSite["lat"]})
        #3)插入聚类点并返回
        aiBusModel.batchClusterSites(insertVals)
        res.update(code=ResponseCode.Success, data={"clusterCorePoints":clusterCorePoints,"clusterAroundPoints":clusterAroundPoints,"clusterOutPoints":clusterOutPoints})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data

@route(cluster,'/removeClusterPoint',methods=["POST"])
@login_required
def removeClusterPoint():
    """
    删除选中的聚类点
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        fileId=data["fileId"]
        relativeId=data["id"]
        row=aiBusModel.invalidClusterSitesBySiteId((userInfo["userName"],fileId,relativeId))
        res.update(code=ResponseCode.Success, data="成功删除{}条记录！".format(row))
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data

@route(cluster,'/addNewClusterPoint',methods=["POST"])
@login_required
def addNewClusterPoint():
    """
    新增聚类点
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        fileId=data["fileId"]
        stationId=data["stationId"]
        stationName=data["stationName"]
        longitude=data["longitude"]
        latitude=data["latitude"]
        number=data["number"]
        row=aiBusModel.insertClusterPoint((fileId,"station_"+str(stationId),stationName,1,1,longitude,latitude,number,userInfo["userName"],userInfo["userName"]))
        res.update(code=ResponseCode.Success, data="成功新增{}条记录！".format(row))
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data