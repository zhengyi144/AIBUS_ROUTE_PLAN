import logging
import json
import uuid
import numpy as np
import itertools
from flask import Blueprint, jsonify, session, request, current_app
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.auth import login_required
from app.utils.util import route
from app.utils.tools import *
from app.utils.amapUtil import get_route_distance_time
from app.utils.GPSConvertUtil import getGPSDistance
from app.models.ai_bus_model import AiBusModel
from app.algorithms.sa import tspSolution,singleRoutePlanSolution

"""
线路规划模块api
"""
routeplan = Blueprint("routeplan", __name__, url_prefix='/routeplan')
logger = logging.getLogger(__name__)

@route(routeplan, '/sortWayPoints', methods=["POST"])
def sortWayPoints():
    """
    利用模拟退火算法对途经点进行排序
    """
    res = ResMsg()
    try:
        data=request.get_json()
        sortPoints,minDist=tspSolution(data["destination"],data["waypoints"])
        res.update(code=ResponseCode.Success,data={"sortPoints":np.array(sortPoints)[:-1].tolist(),"minDist":minDist})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, data="排序报错！")
        return res.data

@route(routeplan, '/planSingleRoute', methods=["POST"])
def planSingleRoute():
    """
    单路线规划
    """
    res = ResMsg()
    try:
        data=request.get_json()
        aiBusModel=AiBusModel()
        fileId=data["fileId"]
        destination=data["destination"]
        waypoints=data["waypoints"]          
        passengers=data["passengers"]         #座位上限
        occupancyRate=float(data["occupancyRate"])    #上座率
        odometerFactor=data["odometerFactor"]   #非直线系数
        roundTrip=data["roundTrip"]   #是否往返0,
        routeFactor=data["routeFactor"]   #路线方案，0时间最短，1距离最短
        MAXNODE=20
        if not destination:
            res.update(code=ResponseCode.Fail,data=[],msg="目的地不能为空！")
            return res.data

        #1)先判断fileid是否为空
        routeNode=[]
        index=0
        if fileId is not None and fileId!='':
            #根据fileId查询文件信息，判断是聚类文件还网点文件
            fileInfo=aiBusModel.selectSiteFileStatus(fileId)
            if fileInfo and fileInfo["clusterStatus"]==1:
                clusterPoints=aiBusModel.selectClusterResult((1,fileId))
                for point in clusterPoints:
                    routeNode.append({"index":index,"nodeName":point["clusterName"],"lng":format(point["longitude"],'.6f'),"lat":format(point["latitude"],'.6f'),"number":point["number"]})
                    index+=1
            else:
                sitePoints=aiBusModel.selectSiteInfoByFileId(fileId)
                for point in sitePoints:
                    routeNode.append({"index":index,"nodeName":point["siteName"],"lng":format(point["longitude"],'.6f'),"lat":format(point["latitude"],'.6f'),"number":point["clientNumber"]})
                    index+=1
        else:
            fileId=-1
        #添加途经点
        for point in waypoints:
            routeNode.append({"index":index,"nodeName":point["siteName"],"lng":format(point["lng"],'.6f'),"lat":format(point["lat"],'.6f'),"number":point["number"]})
            index+=1
        
        #判断结点数量是否超过限制
        if len(routeNode)>MAXNODE:
            res.update(code=ResponseCode.Fail,data=[],msg="路线规划结点数量超过限制！")
            return res.data

        #将目标点一起添加至末尾
        routeNode.append({"index":"dest","nodeName":destination["siteName"],"lng":format(destination["lng"],'.6f'),"lat":format(destination["lat"],'.6f'),"number":0})

        #2)构建结点对，用于获取高德数据
        nodePairDict={}
        routeNodePair=list(itertools.permutations(routeNode, 2))
        for nodePair in routeNodePair:
            key=str(nodePair[0]["index"])+"-"+str(nodePair[1]["index"])
            #先查找数据库是否已经存储好数据
            row=aiBusModel.selectRouteParams((float(nodePair[0]["lng"]),float(nodePair[0]["lat"]),float(nodePair[1]["lng"]),float(nodePair[1]["lat"])))
            if not row:
                fromNode=str(nodePair[0]["lng"])+","+str(nodePair[0]["lat"])
                toNode=str(nodePair[1]["lng"])+","+str(nodePair[1]["lat"])
                distTime=get_route_distance_time(fromNode,toNode)
                directDist=getGPSDistance(float(nodePair[0]["lng"]),float(nodePair[0]["lat"]),float(nodePair[1]["lng"]),float(nodePair[1]["lat"]))
                nodePairDict[key]=distTime
                #存储获取的数据
                startGeo = '{ "type": "Point", "coordinates": [%s, %s]}'%(float(nodePair[0]["lng"]),float(nodePair[0]["lat"]))
                endGeo = '{ "type": "Point", "coordinates": [%s, %s]}'%(float(nodePair[1]["lng"]),float(nodePair[1]["lat"]))
                aiBusModel.inserRouteParams((float(nodePair[0]["lng"]),float(nodePair[0]["lat"]),startGeo,\
                    float(nodePair[1]["lng"]),float(nodePair[1]["lat"]),endGeo,distTime["dist"],distTime["time"],directDist))
            else:
                nodePairDict[key]={"dist":float(row["dist"]),"time":row["time"]}

        routeInfo={"nodePair":nodePairDict,"routeNode":routeNode,"routeFactor":routeFactor,"roundTrip":roundTrip}
        #3)进行路线规划
        solution=singleRoutePlanSolution(routeInfo)
        
        #4)保存路线规划结果,获取最优路径的行程距离、行程时间、直线距离
        routeList=[]
        
        ############往程################
        nodeIndex=0
        routeDist=0
        routeTime=0
        routeNumber=0
        directDist=0
        routeNodeList=[]
        for i in range(len(solution["routeNode"])-1):
            fromNode=solution["routeNode"][i]
            toNode=solution["routeNode"][i+1]
            key=str(fromNode["index"])+"-"+str(toNode["index"])
            routeDist+=nodePairDict[key]["dist"]
            routeTime+=nodePairDict[key]["time"]
            directDist+=getGPSDistance(float(fromNode["lng"]),float(fromNode["lat"]),float(toNode["lng"]),float(toNode["lat"]))
            routeNumber+=fromNode["number"]
            routeNodeList.append({"nodeIndex":nodeIndex,"nodeName":fromNode["nodeName"],\
                "lng":float(fromNode["lng"]),"lat":float(fromNode["lat"]),"number":fromNode["number"],\
                "nextDist":nodePairDict[key]["dist"],"nextTime":nodePairDict[key]["time"]})
            nodeIndex+=1
        #添加终点
        routeNodeList.append({"nodeIndex":nodeIndex,"nodeName":destination["siteName"],\
                "lng":float(destination["lng"]),"lat":float(destination["lat"]),"number":0,"nextDist":0,"nextTime":0})
        
        routeOccupancyRate=float(routeNumber)/passengers*100
        if routeNumber>passengers:
            res.update(code=ResponseCode.Fail,data=[],msg="路线人数超过座位上限！")
            return res.data
        if routeOccupancyRate<occupancyRate:
            res.update(code=ResponseCode.Fail,data=[],msg="路线人数上座率未达到下限！")
            return res.data
        if float(routeDist)/directDist>odometerFactor:
            res.update(code=ResponseCode.Fail,data=[],msg="超过非直线里程系数！")
            return res.data
        #存储路线结点
        routeUuid = uuid.uuid1().int
        aiBusModel.insertRouteInfo((fileId,routeUuid,destination["siteName"],\
            destination["lng"],destination["lat"],passengers,occupancyRate,odometerFactor,\
            routeFactor,roundTrip,json.dumps(waypoints),2))

        for node in routeNodeList:
            aiBusModel.insertRouteDetail((fileId,routeUuid,0,node["nodeIndex"],node["nodeName"],2,\
                node["lng"],node["lat"],node["number"],node["nextDist"],node["nextTime"],1))
        
        #查询路线结点及未规划的结点
        routeNodeResult1=aiBusModel.selectRouteDetail((routeUuid,2,0))
        routeList.append({"routeId":routeUuid,"routeDist":int(routeDist),\
                     "routeTime":routeTime,"routeNumber":routeNumber,\
                    "routeOccupancyRate":routeOccupancyRate,"roundStatus":0,\
                    "routeNodeList":routeNodeResult1,"invalidNodeList":[]})
        
        #############返程################
        if roundTrip==1:
            roundRouteDist=0
            roundRouteTime=0
            roundDirectDist=0
            roundRouteNodeList=[]
            nodeIndex=0

            for i in range(len(solution["routeNode"])-1,0,-1):
                fromNode=solution["routeNode"][i]
                toNode=solution["routeNode"][i-1]
                key=str(fromNode["index"])+"-"+str(toNode["index"])
                roundRouteDist+=nodePairDict[key]["dist"]
                roundRouteTime+=nodePairDict[key]["time"]
                roundDirectDist+=getGPSDistance(float(fromNode["lng"]),float(fromNode["lat"]),float(toNode["lng"]),float(toNode["lat"]))
                roundRouteNodeList.append({"nodeIndex":nodeIndex,"nodeName":fromNode["nodeName"],\
                    "lng":float(fromNode["lng"]),"lat":float(fromNode["lat"]),"number":fromNode["number"],\
                    "nextDist":nodePairDict[key]["dist"],"nextTime":nodePairDict[key]["time"]})
                nodeIndex+=1
                if i==1:
                    roundRouteNodeList.append({"nodeIndex":nodeIndex,"nodeName":toNode["nodeName"],\
                            "lng":float(toNode["lng"]),"lat":float(toNode["lat"]),"number":toNode["number"],\
                            "nextDist":0,"nextTime":0})
            #存储结点
            for node in roundRouteNodeList:
                aiBusModel.insertRouteDetail((fileId,routeUuid,1,node["nodeIndex"],node["nodeName"],2,\
                    node["lng"],node["lat"],node["number"],node["nextDist"],node["nextTime"],1))

            #查询路线结点及未规划的结点
            routeNodeResult2=aiBusModel.selectRouteDetail((routeUuid,2,1))
            routeList.append({"routeId":routeUuid,"routeDist":int(roundRouteDist),\
                     "routeTime":roundRouteTime,"routeNumber":routeNumber,\
                    "routeOccupancyRate":routeOccupancyRate,"roundStatus":1,\
                    "routeNodeList":routeNodeResult2,"invalidNodeList":[]})
        
        res.update(code=ResponseCode.Success,data={"destination":destination,"routeList":routeList})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, msg=str(e))
        return res.data

@route(routeplan, '/reSortRouteNode', methods=["POST"])
def reSortRouteNode():
    """
    调整路径规划结点
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        data=request.get_json()
        fileId=data["fileId"]
        routeId=data["routeId"]
        roundStatus=data["roundStatus"]
        passengers=data["passengers"]
        routeNodeList=data["routeNodeList"]
        invalidNodeList=data["invalidNodeList"]
        if fileId is None or fileId=="":
            res.update(code=ResponseCode.Fail, msg="路线规划保存调整时,fileId不能为空！")
            return res.data
        
        #更新routeInfo参数表,实现之前保存的参数，替换为当前的参数
        if fileId!=-1:
            aiBusModel.invalidRouteInfo((0,fileId))
            aiBusModel.validRouteInfo((1,fileId,routeId))

        #根据routeId删除规划结点
        #aiBusModel.deleteNodesByRouteId((routeId))
        #根据结点顺序获取对应信息
        nodeIndex=0
        newInvalidNodeList=[]
        for node in invalidNodeList:
            aiBusModel.updateRouteDetail((nodeIndex,0,0,0,1,2,routeId,node["id"]))
            newInvalidNodeList.append({"id":node["id"],"nodeIndex":nodeIndex,"nodeName":node["nodeName"],\
                "lng":float(node["lng"]),"lat":float(node["lat"]),"number":node["number"]})
            nodeIndex+=1
        
        nodeIndex=0
        routeDist=0
        routeTime=0
        routeNumber=0
        newRouteNodeList=[]
        length=len(routeNodeList)
        for i in range(length-1):
            fromNode=routeNodeList[i]
            toNode=routeNodeList[i+1]
            row=aiBusModel.selectRouteParams((float(fromNode["lng"]),float(fromNode["lat"]),float(toNode["lng"]),float(toNode["lat"])))
            routeDist+=row["dist"]
            routeTime+=row["time"]
            routeNumber+=fromNode["number"]
            newRouteNodeList.append({"id":fromNode["id"],"nodeIndex":nodeIndex,"nodeName":fromNode["nodeName"],\
                "lng":float(fromNode["lng"]),"lat":float(fromNode["lat"]),"number":fromNode["number"],\
                "nextDist":row["dist"],"nextTime":row["time"]})

            aiBusModel.updateRouteDetail((nodeIndex,1,row["dist"],row["time"],1,roundStatus,routeId,fromNode["id"]))
            nodeIndex+=1
            if i+1==length-1:
                newRouteNodeList.append({"id":toNode["id"],"nodeIndex":nodeIndex,"nodeName":toNode["nodeName"],\
                   "lng":float(toNode["lng"]),"lat":float(toNode["lat"]),"number":toNode["number"],"nextDist":0,"nextTime":0})
                aiBusModel.updateRouteDetail((nodeIndex,1,0,0,1,roundStatus,routeId,toNode["id"]))
                routeNumber+=toNode["number"]
        
        routeOccupancyRate=float(routeNumber)/passengers*100
        result={"routeId":routeId,"routeDist":int(routeDist),\
                    "routeTime":routeTime,"routeNumber":routeNumber,\
                    "routeOccupancyRate":routeOccupancyRate,"routeNodeList":newRouteNodeList,\
                    "invalidNodeList":newInvalidNodeList,"roundStatus":roundStatus}
        
        res.update(code=ResponseCode.Success,data={"routeList":[result]})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, msg="路线规划结点调整报错！")
        return res.data

@route(routeplan, '/queryRoutePlanFileList', methods=["POST"])
@login_required
def queryRoutePlanFileList():
    """
    根据用户权限查询文件列表
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        data=request.get_json()
        clusterStatus=int(data["clusterStatus"])
        userInfo = session.get("userInfo")
        clusterFileList=aiBusModel.selectFileListByClusterStatus(clusterStatus,userInfo["citycode"],userInfo["userNames"])
        res.update(code=ResponseCode.Success, data=clusterFileList)
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, msg="查询聚类文件报错！")
        return res.data

@route(routeplan, '/queryRouteInfo', methods=["POST"])
def queryRouteInfo():
    """
    根据fileId查询路线规矩信息
    """
    res = ResMsg()
    try:
        data=request.get_json()
        aiBusModel=AiBusModel()
        fileId=data["fileId"]
        if fileId is None or fileId=='':
            res.update(code=ResponseCode.Fail,msg="fileId不能为空！")
            return res.data
        #1)查询routeInfo
        routeParams=aiBusModel.selectRouteInfo((fileId))
        if not routeParams:
            res.update(code=ResponseCode.Success)
            return res.data
        routeParams["destination"]={"siteName":routeParams["destName"], "lng":routeParams["destLng"],"lat": routeParams["destLat"]}
        routeParams["waypoints"]=json.loads(routeParams["wayPoints"])
        del routeParams["destName"]
        del routeParams["destLng"]
        del routeParams["destLat"]
        del routeParams["wayPoints"]

        #2)查询路线规划信息
        routeList=[]
        #去程
        routeNodeResult=aiBusModel.selectRouteDetail((routeParams["routeId"],1,0))
        if routeNodeResult and len(routeNodeResult)>0:
            routeTime=0
            routeDist=0
            routeNumber=0
            routeOccupancyRate=0
            for routeNode in routeNodeResult:
                routeTime+=routeNode["nextTime"]
                routeDist+=routeNode["nextDist"]
                routeNumber+=routeNode["number"]
            routeOccupancyRate=float(routeNumber)/routeParams["passengers"]*100
    
            routeList.append({"routeId":routeParams["routeId"],"routeDist":int(routeDist),\
                     "routeTime":routeTime,"routeNumber":routeNumber,\
                    "routeOccupancyRate":routeOccupancyRate,"roundStatus":0,\
                    "routeNodeList":routeNodeResult})
        #返程
        roundRouteNodeResult=aiBusModel.selectRouteDetail((routeParams["routeId"],1,1))
        if roundRouteNodeResult and len(roundRouteNodeResult)>0:
            routeTime=0
            routeDist=0
            routeNumber=0
            routeOccupancyRate=0
            for routeNode in roundRouteNodeResult:
                routeTime+=routeNode["nextTime"]
                routeDist+=routeNode["nextDist"]
                routeNumber+=routeNode["number"]
            routeOccupancyRate=float(routeNumber)/routeParams["passengers"]*100
    
            routeList.append({"routeId":routeParams["routeId"],"routeDist":int(routeDist),\
                     "routeTime":routeTime,"routeNumber":routeNumber,\
                    "routeOccupancyRate":routeOccupancyRate,"roundStatus":1,\
                    "routeNodeList":roundRouteNodeResult})
        
        #未规划的点
        invalidRouteNodeResult=aiBusModel.selectRouteDetail((routeParams["routeId"],1,2))
        invalidNodeList=[]
        for routeNode in invalidRouteNodeResult:
            invalidNodeList.append({"id": routeNode["id"],
                "lat": routeNode["lat"],
                "lng": routeNode["lng"],
                "nodeIndex": routeNode["nodeIndex"],
                "nodeName": routeNode["nodeName"],
                "number": routeNode["number"]})

        del routeParams["routeId"]
        res.update(code=ResponseCode.Success,data={"routeParams":routeParams,"routeList":routeList,"invalidNodeList":invalidNodeList})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, msg="查询路线规划信息报错！")
        return res.data
    
