import logging
import os
from urllib.parse import quote
from flask import Blueprint, jsonify, session, request, current_app,Response
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
            res.update(code=ResponseCode.Fail,msg="该网点文件已经失效!")
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
        res.update(code=ResponseCode.Fail,msg="生成聚类点报错！")
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
            res.update(code=ResponseCode.Fail,msg="该文件已经失效!")
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
            res.update(code=ResponseCode.Fail,msg="网点为空！")
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
            insertVals.append((fileId,relativeId,site["siteName"],site["siteProperty"],0,2,site["lng"],site["lat"],site["number"],str(id),userInfo["userName"],userInfo["userName"]))
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
            insertVals.append((fileId,relativeId,aroundSite["siteName"],aroundSite["siteProperty"],2,2,aroundSite["lng"],aroundSite["lat"],aroundSite["number"],str(id),userInfo["userName"],userInfo["userName"]))
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
            
            #根据site id查询网点信息
            siteInfo=aiBusModel.selectClientNameByIds(item["siteSet"].split(","))
            clientNames=[]
            for site in siteInfo:
                clientNames.append(site["clientName"])

            row={"id":item["id"],"siteName":item["clusterName"],"siteProperty":siteProperty,\
                    "longitude":item["longitude"],"latitude":item["latitude"],"number":item["number"],\
                        "users":item["siteSet"].split(","),"userNames":clientNames}
            if item["clusterProperty"]==1:
                clusterCorePoints.append(row)
            elif item["clusterProperty"]==2:
                clusterAroundPoints.append(row)
            else:
                clusterOutPoints.append(row)
        res.update(code=ResponseCode.Success, data={"clusterCorePoints":clusterCorePoints,"clusterAroundPoints":clusterAroundPoints,"clusterOutPoints":clusterOutPoints})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail,msg="生成聚类点报错！")
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
        clusterAroundPoints=data["clusterAroundPoints"]
        clusterCorePoints=data["clusterCorePoints"]
        clusterOutPoints=data["clusterOutPoints"]
        #1)先判断该文件是网点文件还是聚类结果文件,再更新文件表；
        fileProperty=aiBusModel.selectSiteFileStatus(fileId)
        if fileProperty["clusterStatus"]==1:
            aiBusModel.updateClusterParams((epsRadius,minSamples,userInfo["userName"],fileId))
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
                fileId=clusterFile["id"]
            else:
                aiBusModel.updateClusterParams((epsRadius,minSamples,userInfo["userName"],row["id"]))
                fileId=row["id"]
        #对文件的之前的聚类结果进行失效
        aiBusModel.updateClusterResultByFileId((0,userInfo["userName"],fileId),[1,2])

        #2)插入边界点
        for point in clusterAroundPoints:
            if point["siteProperty"]=="固定":
                relativeProperty=1
            elif point["siteProperty"]=="临时":
                relativeProperty=0
            else:
                relativeProperty=2
            siteSet=",".join(point["users"]).strip(",")

            if point["id"]!="":
                #clusterName=%s,fileId=%s,clusterProperty=%s,clusterStatus=%s,relativeProperty=%s,longitude=%s,latitude=%s, number=%s,siteSet=%s,updateUser=%s
                aiBusModel.updateClusterPointById((point["siteName"],fileId,2,1,relativeProperty, float(point["longitude"]),float(point["latitude"]),point["number"],siteSet,userInfo["userName"],point["id"]))
            else:
                aiBusModel.insertClusterPoint((fileId,"",relativeProperty,point["siteName"],2,1,float(point["longitude"]),float(point["latitude"]),point["number"],siteSet,userInfo["userName"],userInfo["userName"]))
        
        #3)插入聚类点
        for point in clusterCorePoints:
            if point["siteProperty"]=="固定":
                relativeProperty=1
            elif point["siteProperty"]=="临时":
                relativeProperty=0
            else:
                relativeProperty=2
            siteSet=",".join(point["users"]).strip(",")

            if point["id"]!="":
                #clusterName=%s,fileId=%s,clusterProperty=%s,clusterStatus=%s,relativeProperty=%s,longitude=%s,latitude=%s, number=%s,siteSet=%s,updateUser=%s
                aiBusModel.updateClusterPointById((point["siteName"],fileId,1,1,relativeProperty, float(point["longitude"]),float(point["latitude"]),point["number"],siteSet,userInfo["userName"],point["id"]))
            else:
                aiBusModel.insertClusterPoint((fileId,"",relativeProperty,point["siteName"],1,1,float(point["longitude"]),float(point["latitude"]),point["number"],siteSet,userInfo["userName"],userInfo["userName"]))
        
        #4)插入异常点
        for point in clusterOutPoints:
            if point["siteProperty"]=="固定":
                relativeProperty=1
            elif point["siteProperty"]=="临时":
                relativeProperty=0
            else:
                relativeProperty=2
            siteSet=",".join(point["users"]).strip(",")

            if point["id"]!="":
                #clusterName=%s,fileId=%s,clusterProperty=%s,clusterStatus=%s,relativeProperty=%s,longitude=%s,latitude=%s, number=%s,siteSet=%s,updateUser=%s
                aiBusModel.updateClusterPointById((point["siteName"],fileId,0,1,relativeProperty, float(point["longitude"]),float(point["latitude"]),point["number"],siteSet,userInfo["userName"],point["id"]))
            else:
                aiBusModel.insertClusterPoint((fileId,"",relativeProperty,point["siteName"],0,1,float(point["longitude"]),float(point["latitude"]),point["number"],siteSet,userInfo["userName"],userInfo["userName"]))
        
        res.update(code=ResponseCode.Success, msg="成功保存聚类结果！")
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail,msg="保存聚类点保存！")
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
            clusterParams=aiBusModel.selectClusterParamsBySiteFileId((fileId))
            if not clusterParams:
                res.update(code=ResponseCode.Success)
                return res.data
            fileId=clusterParams["id"]
        #2)查询聚类结果
        clusterResut=aiBusModel.selectClusterResult((1,fileId))
        for item in clusterResut:
            if item["relativeProperty"]==1:
                siteProperty="固定"
            elif item["relativeProperty"]==0:
                siteProperty="临时"
            else:
                siteProperty="自定义"
            
            #根据site id查询网点信息
            clientNames=[]
            users=[]
            if item["siteSet"]!='':
                users=item["siteSet"].split(",")
                siteInfo=aiBusModel.selectClientNameByIds(users)
                for site in siteInfo:
                    clientNames.append(site["clientName"])

            row={"id":item["id"],"siteName":item["clusterName"],"siteProperty":siteProperty,\
                    "longitude":item["longitude"],"latitude":item["latitude"],"number":item["number"],\
                        "users":users,"userNames":clientNames}
            if item["clusterProperty"]==1:
                clusterCorePoints.append(row)
            elif item["clusterProperty"]==2:
                clusterAroundPoints.append(row)
            else:
                clusterOutPoints.append(row)
        res.update(code=ResponseCode.Success, data={"epsRadius":clusterParams["clusterRadius"],"minSamples":clusterParams["clusterMinSamples"],"clusterCorePoints":clusterCorePoints,"clusterAroundPoints":clusterAroundPoints,"clusterOutPoints":clusterOutPoints})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail,msg="查询聚类结果报错！")
        return res.data

@route(cluster,'/removeClusterResult',methods=["POST"])
@login_required
def removeClusterResult():
    """
    根据网点文件id，失效网点文件、聚类问件，聚类结果和网点结果
    """
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        fileId=data["fileId"]
        aiBusModel.updateSiteFile((0,0,userInfo["userName"],fileId))
        aiBusModel.updateSiteStatusByfieldId((0,userInfo["userName"],fileId,1))
        aiBusModel.updateClusterResultByFileId((0,userInfo["userName"],fileId),[1,2])
        aiBusModel.updateClusterParams((0,0,userInfo["userName"],fileId))
        res.update(code=ResponseCode.Success, msg="成功删除网点聚类结果!")
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail,msg="删除网点聚类结果报错！")
        return res.data


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
        #sitefileList=aiBusModel.searchSiteListByFileId(fileId)
        # 聚类文件导出
        #1)先查询聚类参数
        clusterParams=aiBusModel.selectClusterParams((fileId))
        if not clusterParams:
            clusterParams=aiBusModel.selectClusterParamsBySiteFileId((fileId))
            if not clusterParams:
                res.update(code=ResponseCode.Success,data={"clusterResult":[]})
                return res.data
            fileId=clusterParams["id"]
        clusterInfo = aiBusModel.searchClusterResult(fileId)
        if None == clusterInfo:
            clusterInfo = []
        res.update(code=ResponseCode.Success, data={"clusterResult":clusterInfo})
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
        siteName=data["siteName"]
        longitude=data["longitude"]
        latitude=data["latitude"]
        number=data["number"]
        siteProperty=data["siteProperty"]
        if siteProperty=="固定":
            relativeProperty=1
        elif siteProperty=="临时":
            relativeProperty=0
        else:
            relativeProperty=2

        row=aiBusModel.selectClusterPointId((fileId,siteName,float(longitude),float(latitude)))
        if row:
            res.update(code=ResponseCode.Fail,msg="新增加的站点己存在!")
            return res.data
        #插入
        aiBusModel.insertClusterPoint((fileId,' ',relativeProperty,siteName,1,2,float(longitude),float(latitude),number,' ',userInfo["userName"],userInfo["userName"]))
        #查找id
        row=aiBusModel.selectClusterPointId((fileId,siteName,float(longitude),float(latitude)))
        res.update(code=ResponseCode.Success, data={"id":row["id"],"siteName":siteName,\
            "longitude":longitude,"latitude":latitude,"number":number,"siteProperty":siteProperty,"users":[]})
        return res.data
    except Exception as e:
        res.update(code=ResponseCode.Fail,msg="新增聚类点报错！")
        return res.data

####################--------前端网页下载excel表格--------###########################
def file_iterator(file_path, chunk_size=512):
    """        
    文件读取迭代器    
    :param file_path:文件路径    
    :param chunk_size: 每次读取流大小    
    :return:   
    """ 
    with open(file_path, 'rb') as target_file: 
        while True:            
            chunk = target_file.read(chunk_size)      
            if chunk:                
                yield chunk            
            else:
                break                


def to_json(obj):
    """
        放置
    :return:
    """
    return json.dumps(obj, ensure_ascii=False)

@route(cluster,'/exportClusterResult',methods=["POST"])
@login_required
def exportClusterResult():
    res = ResMsg()
    try:
        aiBusModel=AiBusModel()
        userInfo = session.get("userInfo")
        data=request.get_json()
        fileId=data["fileId"]
        clusterPoints=[]
        sitePoints=[]
        
        #1)先查询聚类参数
        siteParams=aiBusModel.selectClusterParams((fileId))##根据网点文件fileId的查询网点文件
        if not siteParams:
            siteId = siteParams["id"]
            siteResut=aiBusModel.exportCustomSiteInfo(siteId)
            siteItems =["region", "longitude", "latitude","siteName","siteProperty","clientName","clientProperty","age","clientAddress","number","grade"]
            for item in siteResut:
                if item["siteProperty"]==1:
                    item["siteProperty"]="固定"
                elif item["siteProperty"]==0:
                    item["siteProperty"]="临时"
                else:
                    item["siteProperty"]="自定义"
            
                row=[item["region"],item["longitude"],item["latitude"],item["siteName"],item["siteProperty"],item["clientName"],item["clientProperty"],item["age"],item["clientAddress"],item["number"],item["grade"]]
                sitePoints.append(row)
            writeExcel(fileId,siteItems,sitePoints,0)
            clusterParams=aiBusModel.selectClusterParamsBySiteFileId((fileId))##根据网点文件fileId查询聚类文件
            clusterId=clusterParams["id"]
        else:
            res.update(code=ResponseCode.Success, data={"clusterResult":clusterPoints})
            return res.data
        #2)查询聚类结果
        clusterResut=aiBusModel.exportClusterResult((1,clusterId))
        clusterItems =["region","longitude","latitude","clusterName","relativeProperty", "number"]
        
        for item in clusterResut:
            if item["relativeProperty"]==1:
                item["relativeProperty"]="固定"
            elif item["relativeProperty"]==0:
                item["relativeProperty"]="临时"
            else:
                item["relativeProperty"]="自定义"
            
            clusterrow=[item["region"],item["longitude"],item["latitude"],item["clusterName"],item["relativeProperty"],item["number"]]
            clusterPoints.append(clusterrow)
        file_path = writeExcel(fileId,clusterItems,clusterPoints,1) 
        if file_path is None:        
            return to_json({'success': 0, 'message': '请输入参数'})    
        else:
            if file_path == '':
                return to_json({'success': 0, 'message': '请输入正确路径'})                   
            else:
                if not os.path.isfile(file_path):
                    return to_json({'success': 0, 'message': '文件路径不存在'})                                      
                else:
                    filename = os.path.basename(file_path)#filename=routeplan_student.xls
                    utf_filename=quote(filename.encode('utf-8'))
                    # print(utf_filename)
                    response = Response(file_iterator(file_path))
                    # response.headers['Content-Type'] = 'application/octet-stream'
                    # response.headers["Content-Disposition"] = 'attachment;filename="{}"'.format(filename)
                    response.headers["Content-Disposition"] = "attachment;filename*=UTF-8''{}".format(utf_filename)

                    response.headers['Content-Type'] = "application/octet-stream; charset=UTF-8"
                    #print(response)
                    return response
    except Exception as e:
        res.update(code=ResponseCode.Fail,msg="导出报错！")
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

