import json
from time import time
import uuid
import numpy as np
import itertools
import pandas as pd
from flask import Blueprint, jsonify, session, request, current_app
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.auth import login_required
from app.utils.util import route
from app.utils.tools import *
from app.utils.logger import get_logger
from app.utils.amapUtil import *
from app.utils.GPSConvertUtil import *
from app.models.ai_bus_model import AiBusModel
from app.algorithms.sa import *

"""
线路规划模块api
"""
routeplan = Blueprint("routeplan", __name__, url_prefix='/routeplan')
logger=get_logger(name="routeplan",log_file="logs/logger.log")

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
        logger.info("begin planSingleRoute!")
        data=request.get_json()
        aiBusModel=AiBusModel()
        fileId=data["fileId"]
        destination=data["destination"]
        waypoints=data["waypoints"]          
        passengers=data["passengers"]         #座位上限
        occupancyRate=int(data["occupancyRate"])    #改为上座下限
        #初始化相关系数
        odometerFactor=100.0  
        maxDistance=1000.0*1000  #m
        maxDuration=24*3600  #分钟
        if "odometerFactor" in data and data["odometerFactor"]!="":
            odometerFactor=float(data["odometerFactor"])   #非直线系数(非必选)
        if "maxDistance" in data and data["maxDistance"]!="":
            maxDistance=float(data["maxDistance"])*1000         #最大行程距离,data["maxDistance"](km)
        if "maxDuration" in data and data["maxDuration"]!="":
            maxDuration=float(data["maxDuration"])*60         #最大行程耗时
        roundTrip=data["roundTrip"]   #是否往返0,
        routeFactor=data["routeFactor"]   #路线方案，0时间最短，1距离最短
        vehicleType=int(data["vehicleType"])   #车辆类型0为小车方案，1为货车方案
        MAXNODE=20
        MINNODE=2
        if not destination:
            res.update(code=ResponseCode.Fail,data=[],msg="目的地不能为空！")
            return res.data

        #1)先判断fileid是否为空
        routeNode=[]
        indexList=[]
        index=0
        orderNumber=-1 #订单总数
        if fileId is not None and fileId!='':
            #根据fileId查询文件信息，判断是聚类文件还网点文件
            fileInfo=aiBusModel.selectSiteFileStatus(fileId)
            if fileInfo and fileInfo["clusterStatus"]==1:
                clusterPoints=aiBusModel.selectClusterResult((1,fileId))
                siteInfo=aiBusModel.selectSiteFileStatus(fileInfo["siteFileId"])
                orderNumber=siteInfo["siteCount"]
                for point in clusterPoints:
                    indexList.append(str(index))
                    routeNode.append({"index":index,"nodeName":point["clusterName"],"lng":format(point["longitude"],'.6f'),"lat":format(point["latitude"],'.6f'),"number":point["number"]})
                    index+=1
            else:
                orderNumber=fileInfo["siteCount"]
                sitePoints=aiBusModel.selectSiteInfoByFileId(fileId)
                for point in sitePoints:
                    indexList.append(str(index))
                    routeNode.append({"index":index,"nodeName":point["siteName"],"lng":format(point["longitude"],'.6f'),"lat":format(point["latitude"],'.6f'),"number":point["clientNumber"]})
                    index+=1

            if orderNumber is None or orderNumber<=0:
                orderNumber=passengers
        else:
            fileId=-1
            orderNumber=passengers
        #添加途经点
        for point in waypoints:
            indexList.append(str(index))
            routeNode.append({"index":index,"nodeName":point["siteName"],"lng":format(point["lng"],'.6f'),"lat":format(point["lat"],'.6f'),"number":point["number"]})
            index+=1
        
        #判断结点数量是否超过限制len(routeNode)>MAXNODE or
        if  len(routeNode)<MINNODE:
            res.update(code=ResponseCode.Fail,data=[],msg="路线规划结点数量超过最大限制{}或者小于最小限度{}！".format(MAXNODE,MINNODE))
            return res.data
        
        #判断参数是否冲突
        if occupancyRate>passengers:
            res.update(code=ResponseCode.Fail,data=[],msg="路线规划上座下限必须小于座位上限！")
            return res.data
        """
        if occupancyRate<=0 or occupancyRate>100:
            res.update(code=ResponseCode.Fail,data=[],msg="路线规划上座率下限必须大于{}或者小于{}！".format(0,100))
            return res.data
            
        if passengers<int(orderNumber*occupancyRate/100):
            res.update(code=ResponseCode.Fail,data=[],msg="最低上座率人数超过座位上限！")
            return res.data
        """

        #将目标点一起添加至末尾
        routeNode.append({"index":"dest","nodeName":destination["siteName"],"lng":format(destination["lng"],'.6f'),"lat":format(destination["lat"],'.6f'),"number":0})
        indexList.append("dest")

        #2)构建结点对，用于获取高德数据
        nodePairDict={}
        nodePairList=[]   #用于多线程获取高德数据
        pointNum=len(indexList)
        nodeCostDF=pd.DataFrame(np.zeros([pointNum,pointNum]),columns=indexList,index=indexList)
        routeNodePair=list(itertools.permutations(routeNode, 2))
        paramIds=[]
        for nodePair in routeNodePair:
            fromNode=str(round(float(nodePair[0]["lng"]),6))+","+str(round(float(nodePair[0]["lat"]),6))
            toNode=str(round(float(nodePair[1]["lng"]),6))+","+str(round(float(nodePair[1]["lat"]),6))
            #手动生成id,批量查询
            paramId=generate_md5_key(fromNode+","+toNode)
            paramIds.append(paramId)
        
        #根据paramIds查询缓存的距离nodePairDistList
        nodePairParamsList=aiBusModel.selectRouteParams(vehicleType,paramIds)
        nodePairParamsDict={}
        if nodePairParamsList:
            for item in nodePairParamsList:
                nodePairParamsDict[item["id"]]=item
        
        #获取nodePair的距离
        for nodePair in routeNodePair:
            key=str(nodePair[0]["index"])+"-"+str(nodePair[1]["index"])
            fromNode=str(round(float(nodePair[0]["lng"]),6))+","+str(round(float(nodePair[0]["lat"]),6))
            toNode=str(round(float(nodePair[1]["lng"]),6))+","+str(round(float(nodePair[1]["lat"]),6))
            paramId=generate_md5_key(fromNode+","+toNode)
            #先判断是否已经存在库中
            if paramId in nodePairParamsDict.keys():
                item=nodePairParamsDict[paramId]
                directDist=getGPSDistance(float(nodePair[0]["lng"]),float(nodePair[0]["lat"]),float(nodePair[1]["lng"]),float(nodePair[1]["lat"]))
                nodePairDict[key]={"dist":float(item["dist"]),"time":item["time"],"directDist":directDist}
                #对df进行赋值
                if routeFactor==0:
                    nodeCostDF.loc[str(nodePair[0]["index"]),str(nodePair[1]["index"])]=int(item["time"])
                else:
                    nodeCostDF.loc[str(nodePair[0]["index"]),str(nodePair[1]["index"])]=float(item["dist"])
            else:
                nodePairList.append({"key":key,"origin":fromNode,"destination":toNode,"routeType":vehicleType,"fromNode":nodePair[0],"toNode":nodePair[1],"paramId":paramId})
                
        #从高德获取路径数据
        if len(nodePairList)>0:
            nodePairResult=build_process(nodePairList)
            for item in nodePairList:
                key=item["key"]
                nodeItem=nodePairResult[key]
                directDist=getGPSDistance(float(item["fromNode"]["lng"]),float(item["fromNode"]["lat"]),float(item["toNode"]["lng"]),float(item["toNode"]["lat"]))
                nodePairDict[key]={"dist":nodeItem["dist"],"time":nodeItem["time"],"directDist":directDist}
                #对df进行赋值
                if routeFactor==0:
                    nodeCostDF.loc[str(item["fromNode"]["index"]),str(item["toNode"]["index"])]=nodeItem["time"]
                else:
                    nodeCostDF.loc[str(item["fromNode"]["index"]),str(item["toNode"]["index"])]=nodeItem["dist"]
                
                #存储获取的数据
                if item["paramId"] not in nodePairParamsDict.keys():
                    #startGeo = '{ "type": "Point", "coordinates": [%s, %s]}'%(float(item["fromNode"]["lng"]),float(item["fromNode"]["lat"]))
                    #endGeo = '{ "type": "Point", "coordinates": [%s, %s]}'%(float(item["toNode"]["lng"]),float(item["toNode"]["lat"]))
                    aiBusModel.inserRouteParams((item["paramId"],float(item["fromNode"]["lng"]),float(item["fromNode"]["lat"]),\
                        float(item["toNode"]["lng"]),float(item["toNode"]["lat"]),nodeItem["dist"],nodeItem["time"],directDist,0.0))
                else:
                    aiBusModel.updateRouteParams((nodeItem["dist"],nodeItem["time"],directDist,item["paramId"]))
    
        #3)进行路线规划
        logger.info("start single route plan!")
        solution=singleRoutePlanByGreedyAlgorithm(routeNode,nodePairDict,nodeCostDF,passengers,occupancyRate,orderNumber,odometerFactor,maxDistance,maxDuration)
        if solution["routeNode"] is None:
            res.update(code=ResponseCode.Fail,data=[], msg="未找到满足条件的路线！")
            return res.data
        else:
            #用sa算法进行优化
            routeInfo={"nodePair":nodePairDict,"routeNode":solution["routeNode"],"routeFactor":routeFactor}
            reSolution=singleRoutePlanSolution(routeInfo)
            #print("re bestCost:",reSolution["bestRouteCost"])
            if solution["bestRouteCost"]>reSolution["bestRouteCost"]:
                solution["routeNode"]=reSolution["routeNode"]
            
        #找出最后一段顺路点
        if len(solution["routeNode"])>1:
            lastNode=solution["routeNode"][len(solution["routeNode"])-2]
            fromNode=str(round(float(lastNode["lng"]),6))+","+str(round(float(lastNode["lat"]),6))
            toNode=str(round(float(destination["lng"]),6))+","+str(round(float(destination["lat"]),6))

            polyline=get_driving_polyline(fromNode,toNode)
            solution=findOnwayRouteNode(solution,polyline)

            if solution["routeNumber"]<occupancyRate:
                res.update(code=ResponseCode.Fail,data=[], msg="未找到满足条件的路线！")
                return res.data
                
        logger.info("end single route plan!")

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
        
        #存储路线结点
        routeUuid = uuid.uuid1().int
        aiBusModel.insertRouteInfo((fileId,routeUuid,destination["siteName"],\
            destination["lng"],destination["lat"],passengers,occupancyRate,odometerFactor,\
            routeFactor,roundTrip,json.dumps(waypoints),maxDistance,maxDuration,vehicleType,2))

        for node in routeNodeList:
            aiBusModel.insertRouteDetail((fileId,routeUuid,0,node["nodeIndex"],node["nodeName"],2,\
                node["lng"],node["lat"],node["number"],node["nextDist"],node["nextTime"],1,1))
        
        for i,node in enumerate(solution["invalidRouteNode"]):
            aiBusModel.insertRouteDetail((fileId,routeUuid,0,i,node["nodeName"],2,\
                node["lng"],node["lat"],node["number"],0,0,0,1))

        #查询路线结点及未规划的结点
        routeOccupancyRate=int(routeNumber/orderNumber*100)
        routeNodeResult1=aiBusModel.selectRouteDetail((routeUuid,2,0,1))
        invalidRouteNodeResult=aiBusModel.selectRouteDetail((routeUuid,2,0,0))
        invalidNodeList=[]
        for routeNode in invalidRouteNodeResult:
            invalidNodeList.append({"id": routeNode["id"],
                "lat": routeNode["lat"],
                "lng": routeNode["lng"],
                "nodeIndex": routeNode["nodeIndex"],
                "nodeName": routeNode["nodeName"],
                "number": routeNode["number"]})

        routeList.append({"routeId":routeUuid,"routeDist":int(routeDist),\
                     "routeTime":routeTime,"routeNumber":routeNumber,"orderNumber":orderNumber,\
                    "routeOccupancyRate":routeOccupancyRate,"roundStatus":0,\
                    "routeNodeList":routeNodeResult1,"invalidNodeList":invalidNodeList})
        
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
                    node["lng"],node["lat"],node["number"],node["nextDist"],node["nextTime"],1,1))
            
            for i,node in enumerate(solution["invalidRouteNode"]):
                aiBusModel.insertRouteDetail((fileId,routeUuid,1,i,node["nodeName"],2,\
                    node["lng"],node["lat"],node["number"],0,0,0,1))

            #查询路线结点及未规划的结点
            routeNodeResult2=aiBusModel.selectRouteDetail((routeUuid,2,1,1))
            invalidRouteNodeResult=aiBusModel.selectRouteDetail((routeUuid,2,1,0))
            invalidNodeList=[]
            for routeNode in invalidRouteNodeResult:
                invalidNodeList.append({"id": routeNode["id"],
                    "lat": routeNode["lat"],
                    "lng": routeNode["lng"],
                    "nodeIndex": routeNode["nodeIndex"],
                    "nodeName": routeNode["nodeName"],
                    "number": routeNode["number"]})

            routeList.append({"routeId":routeUuid,"routeDist":int(roundRouteDist),\
                     "routeTime":roundRouteTime,"routeNumber":routeNumber,"orderNumber":orderNumber,\
                    "routeOccupancyRate":routeOccupancyRate,"roundStatus":1,\
                    "routeNodeList":routeNodeResult2,"invalidNodeList":invalidNodeList})
        
        res.update(code=ResponseCode.Success,data={"destination":destination,"routeList":routeList})
        return res.data
    except Exception as e:
        logger.error("planSingleRoute exception:{}".format(str(e)))
        res.update(code=ResponseCode.Fail, msg=str(e))
        return res.data

@route(routeplan, '/reSortRouteNode', methods=["POST"])
def reSortRouteNode():
    """
    调整路径规划结点
    """
    res = ResMsg()
    try:
        logger.info("begin reSortRouteNode!")
        aiBusModel=AiBusModel()
        data=request.get_json()
        fileId=data["fileId"]
        routeId=data["routeId"]
        roundStatus=data["roundStatus"]
        passengers=data["passengers"]
        vehicleType=int(data["vehicleType"])
        routeNodeList=data["routeNodeList"]
        invalidNodeList=data["invalidNodeList"]
        
        #根据结点顺序获取对应信息
        nodeIndex=0
        newInvalidNodeList=[]
        for node in invalidNodeList:
            #aiBusModel.updateRouteDetail((nodeIndex,0,0,0,2,2,routeId,node["id"]))
            newInvalidNodeList.append({"id":node["id"],"nodeIndex":nodeIndex,"nodeName":node["nodeName"],\
                "lng":float(node["lng"]),"lat":float(node["lat"]),"number":node["number"]})
            nodeIndex+=1
        
        nodeIndex=0
        routeDist=0
        routeTime=0
        routeNumber=0
        newRouteNodeList=[]
        length=len(routeNodeList)
        dist=0
        time=0
        for i in range(length-1):
            fromNode=routeNodeList[i]
            toNode=routeNodeList[i+1]
            fromLngLat=str(round(float(fromNode["lng"]),6))+","+str(round(float(fromNode["lat"]),6))
            toLngLat=str(round(float(toNode["lng"]),6))+","+str(round(float(toNode["lat"]),6))
            #手动生成id,批量查询
            paramId=generate_md5_key(fromLngLat+","+toLngLat)
            row=aiBusModel.selectRouteParams(vehicleType,[paramId])
            if row is None or len(row)<1 or row[0]["dist"]:
                startPoint=str(fromNode["lng"])+","+str(fromNode["lat"])
                endPoint=str(toNode["lng"])+","+str(toNode["lat"])
                distTime=get_route_distance_time(startPoint,endPoint,routeType=vehicleType)
                dist+=distTime["dist"]
                time+=distTime["time"]
                routeDist+=distTime["dist"]
                routeTime+=distTime["time"]
            else:
                dist+=row[0]["dist"]
                time+=row[0]["time"]
                routeDist+=row[0]["dist"]
                routeTime+=row[0]["time"]
            #判断结点中type
            if  fromNode["nodeType"]==0:
                newRouteNodeList.append({"nodeIndex":nodeIndex,"nodeName":fromNode["nodeName"],\
                    "lng":float(fromNode["lng"]),"lat":float(fromNode["lat"]),"number":fromNode["number"],\
                    "nextDist":dist,"nextTime":time,"nodeType":fromNode["nodeType"]})
            else:
                routeNumber+=fromNode["number"]
                newRouteNodeList.append({"id":fromNode["id"],"nodeIndex":nodeIndex,"nodeName":fromNode["nodeName"],\
                    "lng":float(fromNode["lng"]),"lat":float(fromNode["lat"]),"number":fromNode["number"],\
                    "nextDist":dist,"nextTime":time,"nodeType":fromNode["nodeType"]})
                dist=0
                time=0

            nodeIndex+=1
            if i+1==length-1:
                newRouteNodeList.append({"id":toNode["id"],"nodeIndex":nodeIndex,"nodeName":toNode["nodeName"],\
                   "lng":float(toNode["lng"]),"lat":float(toNode["lat"]),"number":toNode["number"],"nextDist":0,"nextTime":0,"nodeType":toNode["nodeType"]})
                routeNumber+=toNode["number"]
        
        #获取网点人数
        orderNumber=-1
        fileInfo=aiBusModel.selectSiteFileStatus(fileId)
        if fileInfo:
            if fileInfo["clusterStatus"]==1:
                siteInfo=aiBusModel.selectSiteFileStatus(fileInfo["siteFileId"])
                if siteInfo:
                    orderNumber=siteInfo["siteCount"]
            else:
                orderNumber=fileInfo["siteCount"]
        
        if orderNumber is None or orderNumber<=0:
            orderNumber=passengers
        #返回结果
        routeOccupancyRate=float(routeNumber)/orderNumber*100
        result={"routeId":routeId,"routeDist":int(routeDist),\
                    "routeTime":routeTime,"routeNumber":routeNumber,"orderNumber":orderNumber,\
                    "routeOccupancyRate":routeOccupancyRate,"routeNodeList":newRouteNodeList,\
                    "invalidNodeList":newInvalidNodeList,"roundStatus":roundStatus}

        res.update(code=ResponseCode.Success,data={"routeList":[result]})
        return res.data
    except Exception as e:
        logger.error("reSortRouteNode exception:{}".format(str(e)))
        res.update(code=ResponseCode.Fail, msg="路线规划结点调整报错！")
        return res.data

@route(routeplan,'/saveRouteNode', methods=["POST"])
def saveRouteNode():
    """
    保存规划路线接口
    """
    res = ResMsg()
    try:
        logger.info("begin saveRouteNode!")
        aiBusModel=AiBusModel()
        data=request.get_json()
        fileId=data["fileId"]
        routeId=data["routeId"]
        roundStatus=data["roundStatus"]
        passengers=data["passengers"]
        vehicleType=int(data["vehicleType"])
        routeNodeList=data["routeNodeList"]
        invalidNodeList=data["invalidNodeList"]
        if fileId is None or fileId=="":
            res.update(code=ResponseCode.Fail, msg="路线规划保存时,fileId不能为空！")
            return res.data
        
        #根据结点顺序获取对应信息
        nodeIndex=0
        for node in invalidNodeList:
            aiBusModel.updateRouteDetail((nodeIndex,0,0,0,1,roundStatus,node["nodeName"],node["lng"],node["lat"],routeId,node["id"]))
            #newInvalidNodeList.append({"id":node["id"],"nodeIndex":nodeIndex,"nodeName":node["nodeName"],\
            #    "lng":float(node["lng"]),"lat":float(node["lat"]),"number":node["number"]})
            nodeIndex+=1
        
        #失效所有的途经点
        aiBusModel.invalidWayPoints((routeId))
        nodeIndex=0
        dist=0
        time=0
        length=len(routeNodeList)
        for i in range(length-1):
            fromNode=routeNodeList[i]
            toNode=routeNodeList[i+1]
            fromLngLat=str(round(float(fromNode["lng"]),6))+","+str(round(float(fromNode["lat"]),6))
            toLngLat=str(round(float(toNode["lng"]),6))+","+str(round(float(toNode["lat"]),6))
            #手动生成id,批量查询
            paramId=generate_md5_key(fromLngLat+","+toLngLat)
            row=aiBusModel.selectRouteParams(vehicleType,[paramId])
            if row is None or len(row)<1 or row[0]["dist"]<0.5:
                startPoint=str(fromNode["lng"])+","+str(fromNode["lat"])
                endPoint=str(toNode["lng"])+","+str(toNode["lat"])
                distTime=get_route_distance_time(startPoint,endPoint)
                dist+=distTime["dist"]
                time+=distTime["time"]
            else:
                dist+=row[0]["dist"]
                time+=row[0]["time"]
            
            if  fromNode["nodeType"]==0:
                #fileId,routeId,roundStatus,nodeIndex,nodeName,nodeStatus,nodeLng,nodeLat,number,nextDist,nextTime,nodeProperty,nodeType
                aiBusModel.insertRouteDetail((fileId,routeId,roundStatus,nodeIndex,fromNode["nodeName"],\
                                            1,fromNode["lng"],fromNode["lat"],0,dist,time,1,0))
            else:
                #routeNumber+=fromNode["number"]
                #newRouteNodeList.append({"id":fromNode["id"],"nodeIndex":nodeIndex,"nodeName":fromNode["nodeName"],\
                #    "lng":float(fromNode["lng"]),"lat":float(fromNode["lat"]),"number":fromNode["number"],\
                #    "nextDist":row["dist"],"nextTime":row["time"]})
                aiBusModel.updateRouteDetail((nodeIndex,1,dist,time,1,roundStatus,fromNode["nodeName"],fromNode["lng"],fromNode["lat"],routeId,fromNode["id"]))
                dist=0
                time=0
            nodeIndex+=1
            if i+1==length-1:
                #newRouteNodeList.append({"id":toNode["id"],"nodeIndex":nodeIndex,"nodeName":toNode["nodeName"],\
                #   "lng":float(toNode["lng"]),"lat":float(toNode["lat"]),"number":toNode["number"],"nextDist":0,"nextTime":0})
                aiBusModel.updateRouteDetail((nodeIndex,1,0,0,1,roundStatus,toNode["nodeName"],toNode["lng"],toNode["lat"],routeId,toNode["id"]))
                #routeNumber+=toNode["number"]
                
        #更新routeInfo参数表,实现之前保存的参数，替换为当前的参数
        if fileId!=-1:
            aiBusModel.invalidRouteInfo((0,fileId))
            aiBusModel.validRouteInfo((1,fileId,routeId))

        res.update(code=ResponseCode.Success,msg="路线保存成功！")
        return res.data
    except Exception as e:
        logger.error("saveRouteNode exception:{}".format(str(e)))
        res.update(code=ResponseCode.Fail, msg="路线规划结点保存报错！")
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
        logger.info("begin queryRouteInfo!")
        data=request.get_json()
        aiBusModel=AiBusModel()
        fileId=data["fileId"]
        if fileId is None or fileId=='':
            res.update(code=ResponseCode.Fail,msg="fileId不能为空！")
            return res.data
        #1)查询routeInfo,处理返回路径的基本信息
        routeParams=aiBusModel.selectRouteInfo((fileId))
        if not routeParams:
            res.update(code=ResponseCode.Success)
            return res.data
        routeParams["destination"]={"siteName":routeParams["destName"], "lng":routeParams["destLng"],"lat": routeParams["destLat"]}
        routeParams["waypoints"]=json.loads(routeParams["wayPoints"])
        if routeParams["maxDistance"]!="" and routeParams["maxDistance"]>=1000000.0:
            routeParams["maxDistance"]=""
        elif routeParams["maxDistance"]<1000000.0:
            routeParams["maxDistance"]=routeParams["maxDistance"]/1000
        if routeParams["maxDuration"]!="" and routeParams["maxDuration"]>=24*3600:
            routeParams["maxDuration"]=""

        del routeParams["destName"]
        del routeParams["destLng"]
        del routeParams["destLat"]
        del routeParams["wayPoints"]

        #2)查询路线规划信息
        #获取网点人数
        orderNumber=-1
        fileInfo=aiBusModel.selectSiteFileStatus(fileId)
        if fileInfo:
            if fileInfo["clusterStatus"]==1:
                siteInfo=aiBusModel.selectSiteFileStatus(fileInfo["siteFileId"])
                if siteInfo:
                    orderNumber=siteInfo["siteCount"]
            else:
                orderNumber=fileInfo["siteCount"]
        if orderNumber is None or orderNumber<=0:
            orderNumber=routeParams["passengers"]

        routeList=[]
        #去程
        routeNodeResult=aiBusModel.selectRouteDetail((routeParams["routeId"],1,0,1))

        if routeNodeResult and len(routeNodeResult)>0:
            routeTime=0
            routeDist=0
            routeNumber=0
            routeOccupancyRate=0
            for routeNode in routeNodeResult:
                routeTime+=routeNode["nextTime"]
                routeDist+=routeNode["nextDist"]
                routeNumber+=routeNode["number"]
            routeOccupancyRate=float(routeNumber)/orderNumber*100

            invalidRouteNodeResult=aiBusModel.selectRouteDetail((routeParams["routeId"],1,0,0))
            invalidNodeList=[]
            for routeNode in invalidRouteNodeResult:
                invalidNodeList.append({"id": routeNode["id"],
                    "lat": routeNode["lat"],
                    "lng": routeNode["lng"],
                    "nodeIndex": routeNode["nodeIndex"],
                    "nodeName": routeNode["nodeName"],
                    "number": routeNode["number"]})
    
            routeList.append({"routeId":routeParams["routeId"],"routeDist":int(routeDist),\
                     "routeTime":routeTime,"routeNumber":routeNumber,"orderNumber":orderNumber,\
                    "routeOccupancyRate":routeOccupancyRate,"roundStatus":0,\
                    "routeNodeList":routeNodeResult,"invalidNodeList":invalidNodeList})
        #返程
        roundRouteNodeResult=aiBusModel.selectRouteDetail((routeParams["routeId"],1,1,1))
        if roundRouteNodeResult and len(roundRouteNodeResult)>0:
            routeTime=0
            routeDist=0
            routeNumber=0
            routeOccupancyRate=0
            for routeNode in roundRouteNodeResult:
                routeTime+=routeNode["nextTime"]
                routeDist+=routeNode["nextDist"]
                routeNumber+=routeNode["number"]
            
            invalidRouteNodeResult=aiBusModel.selectRouteDetail((routeParams["routeId"],1,1,0))
            invalidNodeList=[]
            for routeNode in invalidRouteNodeResult:
                invalidNodeList.append({"id": routeNode["id"],
                    "lat": routeNode["lat"],
                    "lng": routeNode["lng"],
                    "nodeIndex": routeNode["nodeIndex"],
                    "nodeName": routeNode["nodeName"],
                    "number": routeNode["number"]})

            routeOccupancyRate=float(routeNumber)/orderNumber*100
    
            routeList.append({"routeId":routeParams["routeId"],"routeDist":int(routeDist),\
                     "routeTime":routeTime,"routeNumber":routeNumber,"orderNumber":orderNumber,\
                    "routeOccupancyRate":routeOccupancyRate,"roundStatus":1,\
                    "routeNodeList":roundRouteNodeResult,"invalidNodeList":invalidNodeList})
        
        #未规划的点
        invalidRouteNodeResult=aiBusModel.selectRouteDetail((routeParams["routeId"],1,2,0))
        invalidNodeList=[]
        for routeNode in invalidRouteNodeResult:
            invalidNodeList.append({"id": routeNode["id"],
                "lat": routeNode["lat"],
                "lng": routeNode["lng"],
                "nodeIndex": routeNode["nodeIndex"],
                "nodeName": routeNode["nodeName"],
                "number": routeNode["number"]})

        del routeParams["routeId"]
        res.update(code=ResponseCode.Success,data={"routeParams":routeParams,"routeList":routeList})
        return res.data
    except Exception as e:
        logger.error("queryRouteInfo exception:{}".format(str(e)))
        res.update(code=ResponseCode.Fail, msg="查询路线规划信息报错！")
        return res.data
    
