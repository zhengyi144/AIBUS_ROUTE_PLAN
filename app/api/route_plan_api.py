import logging
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
        occupancyRate=data["occupancyRate"]    #上座率
        odometerFactor=data["odometerFactor"]   #非直线系数
        roundTrip=data["roundTrip"]   #是否往返0,
        routeFactor=data["routeFactor"]   #路线方案，0时间最短，1距离最短
        if not destination:
            res.update(code=ResponseCode.Fail,data="目的地不能为空！")
            return res.data

        #1)先查询聚类点，聚类点不存在则查询网点
        routeNode=[]
        index=0
        if fileId is not None and fileId!='':
            clusterParams=aiBusModel.selectClusterParams((fileId))
            if clusterParams["clusterStatus"]==1:
                clusterPoints=aiBusModel.selectClusterResult((1,fileId))
                for point in clusterPoints:
                    routeNode.append({"index":index,"nodeName":point["clusterName"],"lng":format(point["longitude"],'.6f'),"lat":format(point["latitude"],'.6f'),"number":point["number"]})
                    index+=1
            else:
                sitePoints=aiBusModel.selectSiteInfoByFileId(fileId)
                for point in sitePoints:
                    routeNode.append({"index":index,"nodeName":point["siteName"],"lng":format(point["longitude"],'.6f'),"lat":format(point["latitude"],'.6f'),"number":point["clientNumber"]})
                    index+=1
        #添加途经点
        for point in waypoints:
            routeNode.append({"index":index,"nodeName":point["siteName"],"lng":format(point["lng"],'.6f'),"lat":format(point["lat"],'.6f'),"number":point["number"]})
            index+=1
        #将目标点一起添加
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
                nodePairDict[key]=distTime
                #存储获取的数据
                startGeo = '{ "type": "Point", "coordinates": [%s, %s]}'%(float(nodePair[0]["lng"]),float(nodePair[0]["lat"]))
                endGeo = '{ "type": "Point", "coordinates": [%s, %s]}'%(float(nodePair[1]["lng"]),float(nodePair[1]["lat"]))
                aiBusModel.inserRouteParams((float(nodePair[0]["lng"]),float(nodePair[0]["lat"]),startGeo,\
                    float(nodePair[1]["lng"]),float(nodePair[1]["lat"]),endGeo,distTime["dist"],distTime["time"]))
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
                "lng":float(fromNode["lng"]),"lat":float(fromNode["lat"]),"number":fromNode["number"]})
            nodeIndex+=1
        #添加终点
        routeNodeList.append({"nodeIndex":nodeIndex,"nodeName":destination["siteName"],\
                "lng":float(destination["lng"]),"lat":float(destination["lat"]),"number":0})
        
        routeOccupancyRate=float(routeNumber)/passengers
        if routeNumber>passengers:
            res.update(code=ResponseCode.Fail,data="路线人数超过座位上限！")
            return res.data
        if routeOccupancyRate<occupancyRate:
            res.update(code=ResponseCode.Fail,data="路线人数上座率未达到下限！")
            return res.data
        if float(routeDist)/directDist>odometerFactor:
            res.update(code=ResponseCode.Fail,data="超过非直线里程系数！")
            return res.data
        #存储路线结点
        routeUuid1 = uuid.uuid1().int
        aiBusModel.insertRouteInfo((routeUuid1,destination["lng"],destination["lat"],passengers,occupancyRate,odometerFactor,routeFactor,0))
        for node in routeNodeList:
            aiBusModel.insertRouteDetail((routeUuid1,node["nodeIndex"],node["nodeName"],1,node["lng"],node["lat"],node["number"]))
        routeList.append({"routeId":routeUuid1,"routeDist":routeDist,\
                     "routeTime":routeTime,"routeNumber":routeNumber,\
                    "routeOccupancyRate":routeOccupancyRate,"roundStatus":0,"routeNodeList":routeNodeList})
        
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
                    "lng":float(fromNode["lng"]),"lat":float(fromNode["lat"]),"number":fromNode["number"]})
                nodeIndex+=1

            #存储结点
            routeUuid2 = uuid.uuid1().int
            aiBusModel.insertRouteInfo((routeUuid2,destination["lng"],destination["lat"],passengers,occupancyRate,odometerFactor,routeFactor,1))
            for node in roundRouteNodeList:
                aiBusModel.insertRouteDetail((routeUuid2,node["nodeIndex"],node["nodeName"],1,node["lng"],node["lat"],node["number"]))

            routeList.append({"routeId":routeUuid2,"routeDist":roundRouteDist,\
                     "routeTime":roundRouteTime,"routeNumber":routeNumber,\
                    "routeOccupancyRate":routeOccupancyRate,"roundStatus":1,"routeNodeList":roundRouteNodeList})
        
        res.update(code=ResponseCode.Success,data={"destination":destination,"routeList":routeList})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, data=str(e))
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
        routeId=data["routeId"]
        passengers=data["passengers"]
        routeNodeList=data["routeNodeList"]
        removeNodeList=data["removeNodeList"]
        #根据routeId删除规划结点
        #aiBusModel.deleteNodesByRouteId((routeId))
        #根据结点顺序获取对应信息
        nodeIndex=0
        newRemoveNodeList=[]
        for node in removeNodeList:
            item=aiBusModel.selectRouteDetail((routeId,node["nodeIndex"]))
            newRemoveNodeList.append({"nodeIndex":nodeIndex,"nodeName":node["nodeName"],\
                "lng":float(node["lng"]),"lat":float(node["lat"]),"number":node["number"]})
            aiBusModel.updateRouteDetail((nodeIndex,0,routeId,item["id"]))
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
            newRouteNodeList.append({"nodeIndex":nodeIndex,"nodeName":fromNode["nodeName"],\
                "lng":float(fromNode["lng"]),"lat":float(fromNode["lat"]),"number":fromNode["number"]})
            item=aiBusModel.selectRouteDetail((routeId,fromNode["nodeIndex"]))
            aiBusModel.updateRouteDetail((nodeIndex,1,routeId,item["id"]))
            nodeIndex+=1
            if i+1==length-1:
                newRouteNodeList.append({"nodeIndex":nodeIndex,"nodeName":toNode["nodeName"],\
                   "lng":float(toNode["lng"]),"lat":float(toNode["lat"]),"number":toNode["number"]})
                item=aiBusModel.selectRouteDetail((routeId,toNode["nodeIndex"]))
                aiBusModel.updateRouteDetail((nodeIndex,1,routeId,item["id"]))
                routeNumber+=toNode["number"]
        
        routeOccupancyRate=float(routeNumber)/passengers
        result={"routeId":routeId,"routeDist":routeDist,\
                    "routeTime":routeTime,"routeNumber":routeNumber,\
                    "routeOccupancyRate":routeOccupancyRate,"routeNodeList":newRouteNodeList,\
                    "removeNodeList":removeNodeList}

        res.update(code=ResponseCode.Success,data=result)
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail, data="路线规划结点调整报错！")
        return res.data