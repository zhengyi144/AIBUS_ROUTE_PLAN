import logging
from flask import Blueprint, jsonify, session, request, current_app
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.auth import login_required
from app.utils.util import route
from app.utils.tools import *
from app.models.ai_bus_model import AiBusModel
from app.algorithms.dbscan import clusterByDbscan,clusterByAdaptiveDbscan

"""
聚类模块api
"""
cluster = Blueprint("cluster", __name__, url_prefix='/cluster')
logger = logging.getLogger(__name__)


@route(cluster,'/generateClusterPointsOld',methods=["POST"])
@login_required
def generateClusterPointsOld():
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
        #if fileStatus["fileProperty"]==0:
        #    res.update(code=ResponseCode.Fail,data="该网点文件还未确认导入!")
        #     return res.data
        if fileStatus["fileStatus"]==0:
            res.update(code=ResponseCode.Fail,data="该网点文件已经失效!")
            return res.data
        #对聚类过的临时结果进行失效
        aiBusModel.updateClusterResultByFileId((0,userInfo["userName"],fileId),[2])

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
            insertVals.append((fileId,relativeId,site["siteName"],site["siteProperty"],0,2,site["lng"],site["lat"],site["number"],"",userInfo["userName"],userInfo["userName"]))
            #clusterOutPoints.append({"id":relativeId,"siteName":site["siteName"],"siteProperty":site["siteProperty"],"number":site["number"],"longitude":site["lng"],"latitude":site["lat"]})

        #2)处理聚类点
        for cluster in clusterInfo["clusterSet"]:
            #处理聚类核心点
            clusterNumber=0
            clusterId=int(cluster["clusterCenterId"])
            site=siteGeoDict[str(clusterId)]
            for id in cluster["clusterCoreIds"]:
                clusterNumber+=siteGeoDict[str(id)]["number"]
            insertVals.append((fileId,"site_"+str(clusterId),site["siteName"],site["siteProperty"],1,2,site["lng"],site["lat"],clusterNumber,",".join(map(str, cluster["clusterCoreIds"])),userInfo["userName"],userInfo["userName"]))
            #clusterCorePoints.append({"id":"site_"+str(clusterId),"siteName":site["siteName"],"siteProperty":site["siteProperty"],"number":clusterNumber,"longitude":site["lng"],"latitude":site["lat"]})
            #处理边界点
            for id in cluster["clusterAroundIds"]:
                relativeId="site_"+str(id)
                aroundSite=siteGeoDict[str(id)]
                insertVals.append((fileId,relativeId,aroundSite["siteName"],aroundSite["siteProperty"],2,2,aroundSite["lng"],aroundSite["lat"],aroundSite["number"],"",userInfo["userName"],userInfo["userName"]))
                #clusterAroundPoints.append({"id":relativeId,"siteName":aroundSite["siteName"],"siteProperty":site["siteProperty"],"number":aroundSite["number"],"longitude":aroundSite["lng"],"latitude":aroundSite["lat"]})
        #3)插入聚类点并返回
        aiBusModel.batchClusterSites(insertVals)

        #4)返回聚类结果
        clusterResut=aiBusModel.selectClusterResult((2,fileId))
        for item in clusterResut:
            if item["relativeProperty"]==1:
                siteProperty="固定"
            elif item["relativeProperty"]==0:
                siteProperty="临时"
            else:
                siteProperty="自定义"
            row={"id":item["id"],"siteName":item["clusterName"],"siteProperty":siteProperty,\
                    "longitude":item["longitude"],"latitude":item["latitude"],"number":item["number"]}
            if item["clusterProperty"]==1:
                clusterCorePoints.append(row)
            elif item["clusterProperty"]==2:
                clusterAroundPoints.append(row)
            else:
                clusterAroundPoints.append(row)
        res.update(code=ResponseCode.Success, data={"clusterCorePoints":clusterCorePoints,"clusterAroundPoints":clusterAroundPoints,"clusterOutPoints":clusterOutPoints})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data

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
        fileProperty=aiBusModel.selectSiteFileStatus(fileId)
        if fileProperty["fileStatus"]==0:
            res.update(code=ResponseCode.Success,data="该文件已经失效!")
            return res.data
        
        #根据网点文件查询网点list
        #先判断是该文件是聚类文件还是网点文件
        if fileProperty["clusterStatus"]==1:
            siteFileId=fileProperty["siteFileId"]  
        else:
            siteFileId=fileId
            #对网点文件的临时聚类结果进行失效
            aiBusModel.updateClusterResultByFileId((0,userInfo["userName"],fileId),[2])

        siteGeoList=aiBusModel.selectSiteGeoListByFileId(siteFileId)
        if not siteGeoList:
            res.update(code=ResponseCode.Success,data="网点为空！")
            return res.data


        #{"noiseList":[ids],"aroundList":[ids],"clusterDict":{"id":[ids],"id":[ids]}}
        clusterInfo=clusterByAdaptiveDbscan(siteGeoList,epsRadius,minSamples)
        #将聚类结果保存至表中
        insertVals=[]
        siteGeoDict={}
        for site in siteGeoList:
            siteGeoDict[str(site["id"])]=site
        
        clusterOutPoints=[]
        clusterCorePoints=[]
        clusterAroundPoints=[]
        #1)处理异常点fileId,siteId,clusterName,clusterProperty,clusterStatus,longitude,latitude,number,siteSet
        for id in clusterInfo["noiseList"]:
            relativeId="site_"+str(id)
            site=siteGeoDict[str(id)]
            insertVals.append((fileId,relativeId,site["siteName"],site["siteProperty"],0,2,site["lng"],site["lat"],site["number"],"",userInfo["userName"],userInfo["userName"]))
            #clusterOutPoints.append({"id":relativeId,"siteName":site["siteName"],"siteProperty":site["siteProperty"],"number":site["number"],"longitude":site["lng"],"latitude":site["lat"]})

        #2)处理聚类点
        for key in clusterInfo["clusterDict"].keys():
            clusterSet=clusterInfo["clusterDict"][key]
            #处理聚类核心点
            clusterNumber=0
            site=siteGeoDict[str(key)]
            for id in clusterSet:
                clusterNumber+=siteGeoDict[str(id)]["number"]
            clusterIdStr=",".join(map(str, clusterSet))
            insertVals.append((fileId,"site_"+str(key),site["siteName"],site["siteProperty"],1,2,site["lng"],site["lat"],clusterNumber,clusterIdStr,userInfo["userName"],userInfo["userName"]))
            #clusterCorePoints.append({"id":"site_"+str(clusterId),"siteName":site["siteName"],"siteProperty":site["siteProperty"],"number":clusterNumber,"longitude":site["lng"],"latitude":site["lat"]})
        #处理边界点
        for id in clusterInfo["aroundList"]:
            relativeId="site_"+str(id)
            aroundSite=siteGeoDict[str(id)]
            insertVals.append((fileId,relativeId,aroundSite["siteName"],aroundSite["siteProperty"],2,2,aroundSite["lng"],aroundSite["lat"],aroundSite["number"],"",userInfo["userName"],userInfo["userName"]))
                #clusterAroundPoints.append({"id":relativeId,"siteName":aroundSite["siteName"],"siteProperty":site["siteProperty"],"number":aroundSite["number"],"longitude":aroundSite["lng"],"latitude":aroundSite["lat"]})
        #3)插入聚类点并返回
        aiBusModel.batchClusterSites(insertVals)

        #4)返回聚类结果
        clusterResut=aiBusModel.selectClusterResult((2,fileId))
        for item in clusterResut:
            if item["relativeProperty"]==1:
                siteProperty="固定"
            elif item["relativeProperty"]==0:
                siteProperty="临时"
            else:
                siteProperty="自定义"
            row={"id":item["id"],"siteName":item["clusterName"],"siteProperty":siteProperty,\
                    "longitude":item["longitude"],"latitude":item["latitude"],"number":item["number"]}
            if item["clusterProperty"]==1:
                clusterCorePoints.append(row)
            elif item["clusterProperty"]==2:
                clusterAroundPoints.append(row)
            else:
                clusterOutPoints.append(row)
        res.update(code=ResponseCode.Success, data={"clusterCorePoints":clusterCorePoints,"clusterAroundPoints":clusterAroundPoints,"clusterOutPoints":clusterOutPoints})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data

@route(cluster,'/saveClusterResult',methods=["POST"])
@login_required
def saveClusterResult():
    """
    保存聚类接口
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        fileId=data["fileId"]
        epsRadius=data["epsRadius"]
        minSamples=data["minSamples"]
        removePoints=data["removePoints"]
        newPoints=data["newPoints"]
        mergePoints=data["mergePoints"]
        #1)先判断该文件是网点文件还是聚类结果文件,再更新文件表；对文件的之前确认的聚类结果进行失效
        aiBusModel.updateClusterResultByFileId((0,userInfo["userName"],fileId),[1])
        fileProperty=aiBusModel.selectSiteFileStatus(fileId)
        if fileProperty["clusterStatus"]==1:
            aiBusModel.updateClusterParams((epsRadius,minSamples,userInfo["userName"],fileId))
            #直接更新聚类结果状态
            aiBusModel.updateClusterResultByFileId((1,userInfo["userName"],fileId),[2])
        else:
            #先判断是否存在聚类文件
            row=aiBusModel.selectClusterFileId((fileProperty["fileName"]+"_聚类",1,fileId))
            if not row:
                #插入新的聚类文件
                #fileName,fileProperty,fileStatus,siteFileId,clusterStatus,clusterRadius,clusterMinSamples,destination,mapType,longitude,latitude,userCitycode,createUser,updateUser
                aiBusModel.insertClusterFile((fileProperty["fileName"]+"_聚类",1,1,fileId,\
                    1,epsRadius,minSamples,fileProperty["destination"],fileProperty["mapType"],
                    fileProperty["longitude"],fileProperty["latitude"],userInfo["citycode"],userInfo["userName"],userInfo["userName"]))
                #查询对应聚类文件id
                clusterFile=aiBusModel.selectClusterFileId((fileProperty["fileName"]+"_聚类",1,fileId))
                #将网点文件的聚类结果关联至聚类文件id,并更新聚类结果状态
                aiBusModel.updateClusterResultByClusterFileId((clusterFile["id"],1,userInfo["userName"],fileId))
                fileId=clusterFile["id"]
            else:
                aiBusModel.updateClusterParams((epsRadius,minSamples,userInfo["userName"],row["id"]))
                #直接更新聚类结果状态
                aiBusModel.updateClusterResultByFileId((1,userInfo["userName"],row["id"]),[2])
                fileId=row["id"]

        #2)先对临时聚类结果进行删除操作
        aiBusModel.invalidClusterSitesById((userInfo["userName"]),removePoints)

        #3)新增聚类点
        for point in newPoints:
            aiBusModel.insertClusterPoint((fileId,"station_"+str(point["id"]),point["stationName"],1,1,point["longitude"],point["latitude"],point["number"],userInfo["userName"],userInfo["userName"]))
        
        #4)合并聚类点，按照顺序合并
        for item in mergePoints:
            #{"originPoint":{"id":23,"label":"C"}, "destPoint":{"id":121,"label":"U"}}
            originPoint=item["originPoint"]
            destPoint=item["destPoint"]
            originInfo=aiBusModel.selectClusterNumberById(fileId,originPoint["id"],originPoint["label"])
            destInfo=aiBusModel.selectClusterNumberById(fileId,destPoint["id"],destPoint["label"])
            #更新destId并失效originId
            aiBusModel.updateClusterPointById((int(destInfo["number"])+int(originInfo["number"]),str(destInfo["siteSet"])+","+str(originInfo["siteSet"]),userInfo["userName"],fileId,destInfo["id"]))
            aiBusModel.invalidClusterSitesById((userInfo["userName"]),[originInfo["id"]])

        res.update(code=ResponseCode.Success, data="成功保存聚类结果！")
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data


@route(cluster,'/queryClusterResult',methods=["POST"])
@login_required
def queryClusterResult():
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        fileId=data["fileId"]
        clusterOutPoints=[]
        clusterCorePoints=[]
        clusterAroundPoints=[]
        #1)先查询聚类参数
        clusterParams=aiBusModel.selectClusterParams((fileId))
        if not clusterParams:
            res.update(code=ResponseCode.Success)
            return res.data
        #2)查询聚类结果
        clusterResut=aiBusModel.selectClusterResult((1,fileId))
        for item in clusterResut:
            if item["relativeProperty"]==1:
                siteProperty="固定"
            elif item["relativeProperty"]==0:
                siteProperty="临时"
            else:
                siteProperty="自定义"
            row={"id":item["id"],"siteName":item["clusterName"],"siteProperty":siteProperty,\
                    "longitude":item["longitude"],"latitude":item["latitude"],"number":item["number"]}
            if item["clusterProperty"]==1:
                clusterCorePoints.append(row)
            elif item["clusterProperty"]==2:
                clusterAroundPoints.append(row)
            else:
                clusterAroundPoints.append(row)
        res.update(code=ResponseCode.Success, data={"epsRadius":clusterParams["clusterRadius"],"minSamples":clusterParams["clusterMinSamples"],"clusterCorePoints":clusterCorePoints,"clusterAroundPoints":clusterAroundPoints,"clusterOutPoints":clusterOutPoints})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data

@route(cluster,'/removeClusterResult',methods=["POST"])
@login_required
def removeClusterResult():
    """
    根据网点文件，失效聚类结果
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        fileId=data["fileId"]
        aiBusModel.updateClusterResultByFileId((0,userInfo["userName"],fileId),[1,2])
        aiBusModel.updateClusterParams((0,0,userInfo["userName"],fileId))
        res.update(code=ResponseCode.Success, data="成功删除聚类结果!")
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data

"""
@route(cluster,'/mergeClusterPoints',methods=["POST"])
@login_required
def mergeClusterPoints():
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        fileId=data["fileId"]
        originId=data["originId"]
        destId=data["destId"]
        #将聚类点的originId合并至destId
        row=aiBusModel.selectClusterNumberById(fileId,[destId,originId])
        #更新destId并失效originId
        aiBusModel.updateClusterPointById((row["number"],row["siteSet"].strip(","),userInfo["userName"],fileId,destId))
        aiBusModel.invalidClusterSitesById((userInfo["userName"],originId))
        res.update(code=ResponseCode.Success, data="成功合并聚类点!")
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data


@route(cluster,'/removeClusterPoint',methods=["POST"])
@login_required
def removeClusterPoint():
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        id=data["id"]
        row=aiBusModel.invalidClusterSitesById((userInfo["userName"],id))
        res.update(code=ResponseCode.Success, data="成功删除{}条记录！".format(row))
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data

@route(cluster,'/addNewClusterPoint',methods=["POST"])
@login_required
def addNewClusterPoint():
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
"""

@route(cluster,'/exportClusterPoints',methods=["POST"])
@login_required
def exportClusterPoints():
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
        # 聚类文件导出
        clusterInfo = aiBusModel.searchClusterResult(fileId)
        if None == clusterInfo:
            clusterInfo = []
        res.update(code=ResponseCode.Success, data={"sitefile":sitefileList,"clusterfile":clusterInfo})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail)
        return res.data