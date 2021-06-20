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
        #根据网点文件查询网点list
        siteGeoList=aiBusModel.selectSiteGeoListByFileId(fileId)
        print(siteGeoList)
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
            site=siteGeoDict[str(id)]
            insertVals.append((fileId,id,site["siteName"],0,1,site["longitude"],site["latitude"],site["number"],""))
            clusterOutPoints.append({"id":id,"siteName":site["siteName"],"number":site["number"],"longitude":site["longitude"],"latitude":site["latitude"]})

        #2)处理聚类点
        for cluster in clusterInfo["clusterSet"]:
            #处理聚类核心点
            clusterNumber=0
            clusterId=int(cluster["clusterCenterId"])
            site=siteGeoDict[str(clusterId)]
            for id in cluster["clusterCoreIds"]:
                clusterNumber+=siteGeoDict[str(id)]["number"]
            insertVals.append(fileId,clusterId,site["siteName"],1,1,site["longitude"],site["latitude"],clusterNumber,",".join(cluster["clusterCoreIds"]))
            clusterCorePoints.append({"id":clusterId,"siteName":site["siteName"],"number":clusterNumber,"longitude":site["longitude"],"latitude":site["latitude"]})
            #处理边界点
            for id in cluster["clusterAroundIds"]:
                aroundSite=siteGeoDict[str(id)]
                insertVals.append((fileId,id,aroundSite["siteName"],2,1,aroundSite["longitude"],aroundSite["latitude"],aroundSite["number"],""))
                clusterAroundPoints.append({"id":id,"siteName":aroundSite["siteName"],"number":aroundSite["number"],"longitude":aroundSite["longitude"],"latitude":aroundSite["latitude"]})
        #3)插入聚类点并返回
        aiBusModel.batchClusterSites(insertVals)
        res.update(code=ResponseCode.Success, data={"clusterCorePoints":clusterCorePoints,"clusterAroundPoints":clusterAroundPoints,"clusterOutPoints":clusterOutPoints})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data